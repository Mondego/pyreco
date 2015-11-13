__FILENAME__ = apt
"""
Search for `apt` packages to include in the blueprint.
"""

import os
import logging
import subprocess

from blueprint import util


def apt(b, r):
    logging.info('searching for APT packages')

    # Define a default output format string for dpkg-query.
    output_format = '${Status}\x1E${binary:Package}\x1E${Version}\n'

    # Try running dpkg --print-foreign-architectures to see if dpkg is
    # multi-arch aware.  If not, revert to old style output_format.
    try:
        with open(os.devnull, 'w') as fnull:
            rv = subprocess.call(['dpkg', '--print-foreign-architectures'],
                                    stdout = fnull, stderr = fnull)
            if rv != 0:
                output_format = '${Status}\x1E${Package}\x1E${Version}\n'
    except OSError:
        return

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Yum/RPM-based
    # system.
    try:
        p = subprocess.Popen(['dpkg-query','-Wf', output_format],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return

    for line in p.stdout:
        status, package, version = line.strip().split('\x1E')
        if 'install ok installed' != status:
            continue
        if r.ignore_package('apt', package):
            continue

        b.add_package('apt', package, version)

        # Create service resources for each service init script or config
        # found in this package.
        p = subprocess.Popen(['dpkg-query', '-L', package],
                             close_fds=True, stdout=subprocess.PIPE)
        for line in p.stdout:
            try:
                manager, service = util.parse_service(line.rstrip())
                if not r.ignore_service(manager, service):
                    b.add_service(manager, service)
                    b.add_service_package(manager, service, 'apt', package)
            except ValueError:
                pass

########NEW FILE########
__FILENAME__ = files
"""
Search for configuration files to include in the blueprint.
"""

import base64
from collections import defaultdict
import errno
import glob
import grp
import hashlib
import logging
import os.path
import pwd
import re
import stat
import subprocess

from blueprint import util


# An extra list of pathnames and MD5 sums that will be checked after no
# match is found in `dpkg`(1)'s list.  If a pathname is given as the value
# then that file's contents will be hashed.
#
# Many of these files are distributed with packages and copied from
# `/usr/share` in the `postinst` program.
#
# XXX Update `blueprintignore`(5) if you make changes here.
MD5SUMS = {'/etc/adduser.conf': ['/usr/share/adduser/adduser.conf'],
           '/etc/apparmor.d/tunables/home.d/ubuntu':
               ['2a88811f7b763daa96c20b20269294a4'],
           '/etc/apt/apt.conf.d/00CDMountPoint':
               ['cb46a4e03f8c592ee9f56c948c14ea4e'],
           '/etc/apt/apt.conf.d/00trustcdrom':
               ['a8df82e6e6774f817b500ee10202a968'],
           '/etc/chatscripts/provider': ['/usr/share/ppp/provider.chatscript'],
           '/etc/default/console-setup':
               ['0fb6cec686d0410993bdf17192bee7d6',
                'b684fd43b74ac60c6bdafafda8236ed3',
                '/usr/share/console-setup/console-setup'],
           '/etc/default/grub': ['ee9df6805efb2a7d1ba3f8016754a119',
                                 'ad9283019e54cedfc1f58bcc5e615dce'],
           '/etc/default/irqbalance': ['7e10d364b9f72b11d7bf7bd1cfaeb0ff'],
           '/etc/default/keyboard': ['06d66484edaa2fbf89aa0c1ec4989857'],
           '/etc/default/locale': ['164aba1ef1298affaa58761647f2ceba',
                                   '7c32189e775ac93487aa4a01dffbbf76'],
           '/etc/default/rcS': ['/usr/share/initscripts/default.rcS'],
           '/etc/environment': ['44ad415fac749e0c39d6302a751db3f2'],
           '/etc/hosts.allow': ['8c44735847c4f69fb9e1f0d7a32e94c1'],
           '/etc/hosts.deny': ['92a0a19db9dc99488f00ac9e7b28eb3d'],
           '/etc/initramfs-tools/modules':
               ['/usr/share/initramfs-tools/modules'],
           '/etc/inputrc': ['/usr/share/readline/inputrc'],
           '/etc/iscsi/iscsid.conf': ['6c6fd718faae84a4ab1b276e78fea471'],
           '/etc/kernel-img.conf': ['f1ed9c3e91816337aa7351bdf558a442'],
           '/etc/ld.so.conf': ['4317c6de8564b68d628c21efa96b37e4'],
           '/etc/ld.so.conf.d/nosegneg.conf':
               ['3c6eccf8f1c6c90eaf3eb486cc8af8a3'],
           '/etc/networks': ['/usr/share/base-files/networks'],
           '/etc/nsswitch.conf': ['/usr/share/base-files/nsswitch.conf'],
           '/etc/pam.d/common-account': ['9d50c7dda6ba8b6a8422fd4453722324'],
           '/etc/pam.d/common-auth': ['a326c972f4f3d20e5f9e1b06eef4d620'],
           '/etc/pam.d/common-password': ['9f2fbf01b1a36a017b16ea62c7ff4c22'],
           '/etc/pam.d/common-session': ['e2b72dd3efb2d6b29698f944d8723ab1'],
           '/etc/pam.d/common-session-noninteractive':
               ['508d44b6daafbc3d6bd587e357a6ff5b'],
           '/etc/pam.d/fingerprint-auth-ac':
               ['d851f318a16c32ed12f5b1cd55e99281'],
           '/etc/pam.d/fingerprint-auth': ['d851f318a16c32ed12f5b1cd55e99281'],
           '/etc/pam.d/password-auth-ac': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/pam.d/password-auth': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/pam.d/smartcard-auth-ac':
               ['dfa6696dc19391b065c45b9525d3ae55'],
           '/etc/pam.d/smartcard-auth': ['dfa6696dc19391b065c45b9525d3ae55'],
           '/etc/pam.d/system-auth-ac': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/pam.d/system-auth': ['e8aee610b8f5de9b6a6cdba8a33a4833'],
           '/etc/ppp/chap-secrets': ['faac59e116399eadbb37644de6494cc4'],
           '/etc/ppp/pap-secrets': ['698c4d412deedc43dde8641f84e8b2fd'],
           '/etc/ppp/peers/provider': ['/usr/share/ppp/provider.peer'],
           '/etc/profile': ['/usr/share/base-files/profile'],
           '/etc/python/debian_config': ['7f4739eb8858d231601a5ed144099ac8'],
           '/etc/rc.local': ['10fd9f051accb6fd1f753f2d48371890'],
           '/etc/rsyslog.d/50-default.conf':
                ['/usr/share/rsyslog/50-default.conf'],
           '/etc/security/opasswd': ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/restorecond.conf':
               ['b5b371cb8c7b33e17bdd0d327fa69b60'],
           '/etc/selinux/targeted/modules/semanage.trans.LOCK':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/modules/active/file_contexts.template':
               ['bfa4d9e76d88c7dc49ee34ac6f4c3925'],
           '/etc/selinux/targeted/modules/active/file_contexts':
               ['1622b57a3b85db3112c5f71238c68d3e'],
           '/etc/selinux/targeted/modules/active/users_extra':
               ['daab665152753da1bf92ca0b2af82999'],
           '/etc/selinux/targeted/modules/active/base.pp':
               ['6540e8e1a9566721e70953a3cb946de4'],
           '/etc/selinux/targeted/modules/active/modules/fetchmail.pp':
               ['0b0c7845f10170a76b9bd4213634cb43'],
           '/etc/selinux/targeted/modules/active/modules/usbmuxd.pp':
               ['72a039c5108de78060651833a073dcd1'],
           '/etc/selinux/targeted/modules/active/modules/pulseaudio.pp':
               ['d9c4f1abf8397d7967bb3014391f7b61'],
           '/etc/selinux/targeted/modules/active/modules/screen.pp':
               ['c343b6c4df512b3ef435f06ed6cfd8b4'],
           '/etc/selinux/targeted/modules/active/modules/cipe.pp':
               ['4ea2d39babaab8e83e29d13d7a83e8da'],
           '/etc/selinux/targeted/modules/active/modules/rpcbind.pp':
               ['48cdaa5a31d75f95690106eeaaf855e3'],
           '/etc/selinux/targeted/modules/active/modules/nut.pp':
               ['d8c81e82747c85d6788acc9d91178772'],
           '/etc/selinux/targeted/modules/active/modules/mozilla.pp':
               ['405329d98580ef56f9e525a66adf7dc5'],
           '/etc/selinux/targeted/modules/active/modules/openvpn.pp':
               ['110fe4c59b7d7124a7d33fda1f31428a'],
           '/etc/selinux/targeted/modules/active/modules/denyhosts.pp':
               ['d12dba0c7eea142c16abd1e0424dfda4'],
           '/etc/selinux/targeted/modules/active/modules/rhcs.pp':
               ['e7a6bf514011f39f277d401cd3d3186a'],
           '/etc/selinux/targeted/modules/active/modules/radius.pp':
               ['a7380d93d0ac922364bc1eda85af80bf'],
           '/etc/selinux/targeted/modules/active/modules/policykit.pp':
               ['1828a7a89c5c7a9cd0bd1b04b379e2c0'],
           '/etc/selinux/targeted/modules/active/modules/varnishd.pp':
               ['260ef0797e6178de4edeeeca741e2374'],
           '/etc/selinux/targeted/modules/active/modules/bugzilla.pp':
               ['c70402a459add46214ee370039398931'],
           '/etc/selinux/targeted/modules/active/modules/java.pp':
               ['ac691d90e755a9a929c1c8095d721899'],
           '/etc/selinux/targeted/modules/active/modules/courier.pp':
               ['d6eb2ef77d755fd49d61e48383867ccb'],
           '/etc/selinux/targeted/modules/active/modules/userhelper.pp':
               ['787e5ca0ee1c9e744e9116837d73c2b9'],
           '/etc/selinux/targeted/modules/active/modules/sssd.pp':
               ['aeb11626d9f34af08e9cd50b1b5751c7'],
           '/etc/selinux/targeted/modules/active/modules/munin.pp':
               ['db2927d889a3dfbe439eb67dfdcba61d'],
           '/etc/selinux/targeted/modules/active/modules/ppp.pp':
               ['7c6f91f4aae1c13a3d2a159a4c9b8553'],
           '/etc/selinux/targeted/modules/active/modules/xfs.pp':
               ['6b3be69f181f28e89bfcffa032097dcb'],
           '/etc/selinux/targeted/modules/active/modules/consolekit.pp':
               ['ef682e07a732448a12f2e93da946d655'],
           '/etc/selinux/targeted/modules/active/modules/telnet.pp':
               ['43fd78d022e499bcb6392da33ed6e28d'],
           '/etc/selinux/targeted/modules/active/modules/nagios.pp':
               ['9c9e482867dce0aa325884a50a023a83'],
           '/etc/selinux/targeted/modules/active/modules/sysstat.pp':
               ['0fc4e6b3472ce5e8cfd0f3e785809552'],
           '/etc/selinux/targeted/modules/active/modules/tor.pp':
               ['2c926e3c5b79879ed992b72406544394'],
           '/etc/selinux/targeted/modules/active/modules/qpidd.pp':
               ['959d4763313e80d8a75bc009094ea085'],
           '/etc/selinux/targeted/modules/active/modules/radvd.pp':
               ['a7636d3df0f431ad421170150e8a9d2e'],
           '/etc/selinux/targeted/modules/active/modules/aiccu.pp':
               ['c0eafc1357cd0c07be4034c1a27ada98'],
           '/etc/selinux/targeted/modules/active/modules/tgtd.pp':
               ['55da30386834e60a10b4bab582a1b689'],
           '/etc/selinux/targeted/modules/active/modules/sectoolm.pp':
               ['6f8fba8d448da09f85a03622de295ba9'],
           '/etc/selinux/targeted/modules/active/modules/unconfineduser.pp':
               ['0bc2f6faf3b38a657c4928ec7b611d7a'],
           '/etc/selinux/targeted/modules/active/modules/sambagui.pp':
               ['31a5121c80a6114b25db4984bdf8d999'],
           '/etc/selinux/targeted/modules/active/modules/mpd.pp':
               ['cdabce7844a227a81c2334dec0c49e9b'],
           '/etc/selinux/targeted/modules/active/modules/hddtemp.pp':
               ['76d85610a7e198c82406d850ccd935e1'],
           '/etc/selinux/targeted/modules/active/modules/clamav.pp':
               ['f8f5b60e3f5b176810ea0666b989f63d'],
           '/etc/selinux/targeted/modules/active/modules/tvtime.pp':
               ['886dc0a6e9ebcbb6787909851e7c209f'],
           '/etc/selinux/targeted/modules/active/modules/cgroup.pp':
               ['9e1cd610b6fde0e9b42cabd7f994db46'],
           '/etc/selinux/targeted/modules/active/modules/rshd.pp':
               ['e39cec5e9ade8a619ecb91b85a351408'],
           '/etc/selinux/targeted/modules/active/modules/roundup.pp':
               ['133b9b3b2f70422953851e18d6c24276'],
           '/etc/selinux/targeted/modules/active/modules/virt.pp':
               ['9ae34fca60c651c10298797c1260ced0'],
           '/etc/selinux/targeted/modules/active/modules/asterisk.pp':
               ['f823fdcb2c6df4ddde374c9edb11ef26'],
           '/etc/selinux/targeted/modules/active/modules/livecd.pp':
               ['8972e6ef04f490b8915e7983392b96ce'],
           '/etc/selinux/targeted/modules/active/modules/netlabel.pp':
               ['91fc83e5798bd271742823cbb78c17ff'],
           '/etc/selinux/targeted/modules/active/modules/qemu.pp':
               ['e561673d5f9e5c19bcae84c1641fa4a7'],
           '/etc/selinux/targeted/modules/active/modules/unconfined.pp':
               ['3acd5dceb6b7a71c32919c29ef920785'],
           '/etc/selinux/targeted/modules/active/modules/postgresql.pp':
               ['3ecc9f2c7b911fa37d8ab6cc1c6b0ea7'],
           '/etc/selinux/targeted/modules/active/modules/apache.pp':
               ['c0089e4472399e9bc5237b1e0485ac39'],
           '/etc/selinux/targeted/modules/active/modules/abrt.pp':
               ['09e212789d19f41595d7952499236a0c'],
           '/etc/selinux/targeted/modules/active/modules/rsync.pp':
               ['e2567e8716c116ea6324c77652c97137'],
           '/etc/selinux/targeted/modules/active/modules/git.pp':
               ['7904fd9fbae924be5377ccd51036248e'],
           '/etc/selinux/targeted/modules/active/modules/amanda.pp':
               ['594eddbbe3b4530e79702fc6a882010e'],
           '/etc/selinux/targeted/modules/active/modules/cvs.pp':
               ['62cf7b7d58f507cc9f507a6c303c8020'],
           '/etc/selinux/targeted/modules/active/modules/chronyd.pp':
               ['a4ff3e36070d461771230c4019b23440'],
           '/etc/selinux/targeted/modules/active/modules/gpm.pp':
               ['ed3f26e774be81c2cbaaa87dcfe7ae2d'],
           '/etc/selinux/targeted/modules/active/modules/modemmanager.pp':
               ['840d4da9f32a264436f1b22d4d4a0b2a'],
           '/etc/selinux/targeted/modules/active/modules/podsleuth.pp':
               ['67e659e9554bc35631ee829b5dc71647'],
           '/etc/selinux/targeted/modules/active/modules/publicfile.pp':
               ['0f092d92c326444dc9cee78472c56655'],
           '/etc/selinux/targeted/modules/active/modules/postfix.pp':
               ['a00647ad811c22810c76c1162a97e74b'],
           '/etc/selinux/targeted/modules/active/modules/exim.pp':
               ['8c3cd1fbd8f68e80ac7707f243ac1911'],
           '/etc/selinux/targeted/modules/active/modules/telepathy.pp':
               ['9b32f699beb6f9c563f06f6b6d76732c'],
           '/etc/selinux/targeted/modules/active/modules/amtu.pp':
               ['1b87c9fef219244f80b1f8f57a2ce7ea'],
           '/etc/selinux/targeted/modules/active/modules/bitlbee.pp':
               ['cf0973c8fff61577cf330bb74ef75eed'],
           '/etc/selinux/targeted/modules/active/modules/memcached.pp':
               ['0146491b4ab9fbd2854a7e7fb2092168'],
           '/etc/selinux/targeted/modules/active/modules/sandbox.pp':
               ['82502d6d11b83370d1a77343f20d669f'],
           '/etc/selinux/targeted/modules/active/modules/dictd.pp':
               ['6119d37987ea968e90a39d96866e5805'],
           '/etc/selinux/targeted/modules/active/modules/pingd.pp':
               ['16c40af7785c8fa9d40789284ce8fbb9'],
           '/etc/selinux/targeted/modules/active/modules/milter.pp':
               ['acaec7d2ee341e97ac5e345b55f6c7ae'],
           '/etc/selinux/targeted/modules/active/modules/snort.pp':
               ['25f360aa5dec254a8fc18262bbe40510'],
           '/etc/selinux/targeted/modules/active/modules/cups.pp':
               ['5323d417895d5ab508048e2bc45367bf'],
           '/etc/selinux/targeted/modules/active/modules/rdisc.pp':
               ['5bed79cb1f4d5a2b822d6f8dbf53fe97'],
           '/etc/selinux/targeted/modules/active/modules/rlogin.pp':
               ['6f88cc86985b4bc79d4b1afbffb1a732'],
           '/etc/selinux/targeted/modules/active/modules/openct.pp':
               ['884f078f5d12f7b1c75cf011a94746e1'],
           '/etc/selinux/targeted/modules/active/modules/dbskk.pp':
               ['caa93f24bfeede892fd97c59ee8b61da'],
           '/etc/selinux/targeted/modules/active/modules/bluetooth.pp':
               ['ce4f1b34168c537b611783033316760e'],
           '/etc/selinux/targeted/modules/active/modules/gpsd.pp':
               ['dd15485b8c6e5aeac018ddbe0948464c'],
           '/etc/selinux/targeted/modules/active/modules/tuned.pp':
               ['5fc9de20402245e4a1a19c5b31101d06'],
           '/etc/selinux/targeted/modules/active/modules/piranha.pp':
               ['fcedf8588c027633bedb76b598b7586f'],
           '/etc/selinux/targeted/modules/active/modules/vhostmd.pp':
               ['0ca7152ed8a0ae393051876fe89ed657'],
           '/etc/selinux/targeted/modules/active/modules/corosync.pp':
               ['20518dface3d23d7408dd56a51c8e6e1'],
           '/etc/selinux/targeted/modules/active/modules/clogd.pp':
               ['533994a32ecf847a3162675e171c847c'],
           '/etc/selinux/targeted/modules/active/modules/samba.pp':
               ['c7cd9b91a5ba4f0744e3f55a800f2831'],
           '/etc/selinux/targeted/modules/active/modules/howl.pp':
               ['fef7dd76a97921c3e5e0e66fbac15091'],
           '/etc/selinux/targeted/modules/active/modules/shutdown.pp':
               ['55f36d9820dcd19c66729d446d3ce6b2'],
           '/etc/selinux/targeted/modules/active/modules/oddjob.pp':
               ['54d59b40e7bc0dc0dee3882e6c0ce9f3'],
           '/etc/selinux/targeted/modules/active/modules/pcscd.pp':
               ['e728f332850dfcb5637c4e8f220af2fc'],
           '/etc/selinux/targeted/modules/active/modules/canna.pp':
               ['de4f1a3ada6f9813da36febc31d2a282'],
           '/etc/selinux/targeted/modules/active/modules/arpwatch.pp':
               ['0ddc328fa054f363a035ba44ec116514'],
           '/etc/selinux/targeted/modules/active/modules/seunshare.pp':
               ['64844bbf79ee23e087a5741918f3a7ad'],
           '/etc/selinux/targeted/modules/active/modules/rhgb.pp':
               ['c9630cc5830fcb4b775985c5740f5a71'],
           '/etc/selinux/targeted/modules/active/modules/prelude.pp':
               ['2b85511c571c19751bb79b288267661c'],
           '/etc/selinux/targeted/modules/active/modules/portmap.pp':
               ['231abe579c0370f49cac533c6057792b'],
           '/etc/selinux/targeted/modules/active/modules/logadm.pp':
               ['980b1345ef8944a90b6efdff0c8b3278'],
           '/etc/selinux/targeted/modules/active/modules/ptchown.pp':
               ['987fc8a6ff50ef7eed0edc79f91b1ec5'],
           '/etc/selinux/targeted/modules/active/modules/vmware.pp':
               ['8cf31ec8abd75f2a6c56857146caf5a1'],
           '/etc/selinux/targeted/modules/active/modules/portreserve.pp':
               ['0354f017b429dead8de0d143f7950fcc'],
           '/etc/selinux/targeted/modules/active/modules/awstats.pp':
               ['c081d3168b28765182bb4ec937b4c0b1'],
           '/etc/selinux/targeted/modules/active/modules/tmpreaper.pp':
               ['ac0173dd09a54a87fdcb42d3a5e29442'],
           '/etc/selinux/targeted/modules/active/modules/postgrey.pp':
               ['68013352c07570ac38587df9fb7e88ee'],
           '/etc/selinux/targeted/modules/active/modules/tftp.pp':
               ['a47fb7872bfb06d80c8eef969d91e6f9'],
           '/etc/selinux/targeted/modules/active/modules/rgmanager.pp':
               ['1cee78e1ff3f64c4d013ce7b820e534b'],
           '/etc/selinux/targeted/modules/active/modules/aisexec.pp':
               ['95e70fd35e9cb8284488d6bf970815b7'],
           '/etc/selinux/targeted/modules/active/modules/xguest.pp':
               ['d8df4b61df93008cd594f98c852d4cba'],
           '/etc/selinux/targeted/modules/active/modules/cobbler.pp':
               ['6978d8b37b1da384130db5c5c2144175'],
           '/etc/selinux/targeted/modules/active/modules/mysql.pp':
               ['d147af479531042f13e70d72bd58a0e9'],
           '/etc/selinux/targeted/modules/active/modules/amavis.pp':
               ['7fc17b2f47c1d8226a9003df1ef67bb5'],
           '/etc/selinux/targeted/modules/active/modules/fprintd.pp':
               ['d58f18b496f69a74ece1f1b1b9432405'],
           '/etc/selinux/targeted/modules/active/modules/nis.pp':
               ['d696b167de5817226298306c79761fa2'],
           '/etc/selinux/targeted/modules/active/modules/squid.pp':
               ['3f9e075e79ec5aa59609a7ccebce0afe'],
           '/etc/selinux/targeted/modules/active/modules/smokeping.pp':
               ['98b83cac4488d7dd18c479b62dd3cf15'],
           '/etc/selinux/targeted/modules/active/modules/ktalk.pp':
               ['afe14e94861782679305c91da05e7d5e'],
           '/etc/selinux/targeted/modules/active/modules/certwatch.pp':
               ['bf13c9a642ded8354ba26d5462ddd60c'],
           '/etc/selinux/targeted/modules/active/modules/games.pp':
               ['3bcd17c07699d58bd436896e75a24520'],
           '/etc/selinux/targeted/modules/active/modules/zabbix.pp':
               ['5445ccfec7040ff1ccf3abf4de2e9a3c'],
           '/etc/selinux/targeted/modules/active/modules/rwho.pp':
               ['710e29c8e621de6af9ca74869624b9f0'],
           '/etc/selinux/targeted/modules/active/modules/w3c.pp':
               ['aea6b9518cb3fa904cc7ee82239b07c2'],
           '/etc/selinux/targeted/modules/active/modules/cyphesis.pp':
               ['dccb3f009cd56c5f8856861047d7f2ff'],
           '/etc/selinux/targeted/modules/active/modules/kismet.pp':
               ['f2d984e007275d35dd03a2d59ade507e'],
           '/etc/selinux/targeted/modules/active/modules/zosremote.pp':
               ['77a2681c4b1c3c001faeca9874b58ecf'],
           '/etc/selinux/targeted/modules/active/modules/pads.pp':
               ['76b7413009a202e228ee08c5511f3f42'],
           '/etc/selinux/targeted/modules/active/modules/avahi.pp':
               ['b59670ba623aba37ab8f0f1f1127893a'],
           '/etc/selinux/targeted/modules/active/modules/apcupsd.pp':
               ['81fae28232730a49b7660797ef4354c3'],
           '/etc/selinux/targeted/modules/active/modules/usernetctl.pp':
               ['22850457002a48041d885c0d74fbd934'],
           '/etc/selinux/targeted/modules/active/modules/finger.pp':
               ['5dd6b44358bbfabfdc4f546e1ed34370'],
           '/etc/selinux/targeted/modules/active/modules/dhcp.pp':
               ['7e63b07b64848a017eec5d5f6b88f22e'],
           '/etc/selinux/targeted/modules/active/modules/xen.pp':
               ['67086e8e94bdaab8247ac4d2e23162d1'],
           '/etc/selinux/targeted/modules/active/modules/plymouthd.pp':
               ['1916027e7c9f28430fa2ac30334e8964'],
           '/etc/selinux/targeted/modules/active/modules/uucp.pp':
               ['5bec7a345a314a37b4a2227bdfa926f1'],
           '/etc/selinux/targeted/modules/active/modules/daemontools.pp':
               ['aad7633adfc8b04e863b481deebaf14a'],
           '/etc/selinux/targeted/modules/active/modules/kdumpgui.pp':
               ['66e08b4187623fa1c535972a35ec058c'],
           '/etc/selinux/targeted/modules/active/modules/privoxy.pp':
               ['f13c986051659fa900786ea54a59ceae'],
           '/etc/selinux/targeted/modules/active/modules/unprivuser.pp':
               ['a0d128b495a6ea5da72c849ac63c5848'],
           '/etc/selinux/targeted/modules/active/modules/ada.pp':
               ['a75fd52c873e2c9326ad87f7515a664f'],
           '/etc/selinux/targeted/modules/active/modules/lircd.pp':
               ['3cc5cc5b24d40416f9d630a80005d33b'],
           '/etc/selinux/targeted/modules/active/modules/openoffice.pp':
               ['522c3ee13bc37cbe9903d00f0cbccd1d'],
           '/etc/selinux/targeted/modules/active/modules/puppet.pp':
               ['9da4c553f40f3dea876171e672168044'],
           '/etc/selinux/targeted/modules/active/modules/wine.pp':
               ['31c470eabd98c5a5dbc66ba52ad64de0'],
           '/etc/selinux/targeted/modules/active/modules/ulogd.pp':
               ['065551ea63de34a7257ecec152f61552'],
           '/etc/selinux/targeted/modules/active/modules/mplayer.pp':
               ['f889dbfa3d9ef071d8e569def835a2f3'],
           '/etc/selinux/targeted/modules/active/modules/ftp.pp':
               ['75a9f3563903eb8126ffbcc9277e1d8c'],
           '/etc/selinux/targeted/modules/active/modules/gnome.pp':
               ['b859e2d45123f60ff27a90cdb0f40e1b'],
           '/etc/selinux/targeted/modules/active/modules/ethereal.pp':
               ['8963c6b80025b27850f0cdf565e5bd54'],
           '/etc/selinux/targeted/modules/active/modules/iscsi.pp':
               ['7786cb4a84889010751b4d89c72a2956'],
           '/etc/selinux/targeted/modules/active/modules/chrome.pp':
               ['cb44c1c7b13cc04c07c4e787a259b63f'],
           '/etc/selinux/targeted/modules/active/modules/guest.pp':
               ['308d614589af73e39a22e5c741e9eecb'],
           '/etc/selinux/targeted/modules/active/modules/inn.pp':
               ['8d60592dcd3bf4d2fa97f0fefa9374ca'],
           '/etc/selinux/targeted/modules/active/modules/gitosis.pp':
               ['21c79a711157224bebba0a2cccbe8881'],
           '/etc/selinux/targeted/modules/active/modules/ksmtuned.pp':
               ['8f985e777c206d2bde3fc2ac6a28cd24'],
           '/etc/selinux/targeted/modules/active/modules/sosreport.pp':
               ['9b4780d27555e94335f80a0bb2ab4f14'],
           '/etc/selinux/targeted/modules/active/modules/ipsec.pp':
               ['68cacb8c78796957fb4a181390033b16'],
           '/etc/selinux/targeted/modules/active/modules/comsat.pp':
               ['1cecb3f5cbe24251017908e14838ee2a'],
           '/etc/selinux/targeted/modules/active/modules/gpg.pp':
               ['75358ddabb045e91010d80f1ab68307a'],
           '/etc/selinux/targeted/modules/active/modules/gnomeclock.pp':
               ['a4e74df48faab3af8f4df0fa16c65c7e'],
           '/etc/selinux/targeted/modules/active/modules/sasl.pp':
               ['5ba9be813a7dd4236fc2d37bc17c5052'],
           '/etc/selinux/targeted/modules/active/modules/vpn.pp':
               ['32ae00c287432ae5ad4f8affbc9e44fe'],
           '/etc/selinux/targeted/modules/active/modules/accountsd.pp':
               ['308057b48c6d70a45e5a603dbe625c2d'],
           '/etc/selinux/targeted/modules/active/modules/devicekit.pp':
               ['1f5a8f12ebeebfed2cfeb3ee4648dd13'],
           '/etc/selinux/targeted/modules/active/modules/psad.pp':
               ['b02f11705249c93735f019f5b97fdf7b'],
           '/etc/selinux/targeted/modules/active/modules/mono.pp':
               ['8bba1cc6826e8300c140f9c393ad07e9'],
           '/etc/selinux/targeted/modules/active/modules/cachefilesd.pp':
               ['82b93ba87b5920ecc8a7388f4cf8ea43'],
           '/etc/selinux/targeted/modules/active/modules/usbmodules.pp':
               ['20c3a57da3c1311a75a63f1c6ae91bf3'],
           '/etc/selinux/targeted/modules/active/modules/certmonger.pp':
               ['b9fe8ba6abc5204cd8eec546f5614ff5'],
           '/etc/selinux/targeted/modules/active/modules/pegasus.pp':
               ['bb0ec4379c28b196d1794d7310111d98'],
           '/etc/selinux/targeted/modules/active/modules/ntop.pp':
               ['99b46fe44ccf3c4e045dbc73d2a88f59'],
           '/etc/selinux/targeted/modules/active/modules/zebra.pp':
               ['12adcaae458d18f650578ce25e10521a'],
           '/etc/selinux/targeted/modules/active/modules/soundserver.pp':
               ['583abd9ccef70279bff856516974d471'],
           '/etc/selinux/targeted/modules/active/modules/stunnel.pp':
               ['2693ac1bf08287565c3b4e58d0f9ea55'],
           '/etc/selinux/targeted/modules/active/modules/ldap.pp':
               ['039baf0976f316c3f209a5661174a72e'],
           '/etc/selinux/targeted/modules/active/modules/fail2ban.pp':
               ['ce13513c427ff140bf988b01bd52e886'],
           '/etc/selinux/targeted/modules/active/modules/spamassassin.pp':
               ['e02232992676b0e1279c54bfeea290e3'],
           '/etc/selinux/targeted/modules/active/modules/procmail.pp':
               ['d5c58e90fac452a1a6d68cc496e7f1ae'],
           '/etc/selinux/targeted/modules/active/modules/afs.pp':
               ['6e7a4bf08dc7fa5a0f97577b913267ad'],
           '/etc/selinux/targeted/modules/active/modules/ricci.pp':
               ['8b1d44245be204907c82c3580a43901d'],
           '/etc/selinux/targeted/modules/active/modules/qmail.pp':
               ['ea08eb2172c275598d4f85c9b78182cd'],
           '/etc/selinux/targeted/modules/active/modules/ccs.pp':
               ['cad223d57f431e2f88a1d1542c2ac504'],
           '/etc/selinux/targeted/modules/active/modules/audioentropy.pp':
               ['19f6fd5e3ee2a3726a952631e993a133'],
           '/etc/selinux/targeted/modules/active/modules/ncftool.pp':
               ['c15f4833a21e9c8cd1237ee568aadcf3'],
           '/etc/selinux/targeted/modules/active/modules/nx.pp':
               ['3677983206101cfcd2182e180ef3876b'],
           '/etc/selinux/targeted/modules/active/modules/rtkit.pp':
               ['0eaae15f4c12522270b26769487a06e0'],
           '/etc/selinux/targeted/modules/active/modules/ntp.pp':
               ['141339ee3372e07d32575c6777c8e466'],
           '/etc/selinux/targeted/modules/active/modules/likewise.pp':
               ['b5f0d18f8b601e102fd9728fbb309692'],
           '/etc/selinux/targeted/modules/active/modules/aide.pp':
               ['69600bc8a529f8128666a563c7409929'],
           '/etc/selinux/targeted/modules/active/modules/nslcd.pp':
               ['5c87b1c80bdd8bbf60c33ef51a765a93'],
           '/etc/selinux/targeted/modules/active/modules/slocate.pp':
               ['fdea88c374382f3d652a1ac529fbd189'],
           '/etc/selinux/targeted/modules/active/modules/execmem.pp':
               ['44cc2d117e3bf1a33d4e3516aaa7339d'],
           '/etc/selinux/targeted/modules/active/modules/cpufreqselector.pp':
               ['7da9c9690dc4f076148ef35c3644af13'],
           '/etc/selinux/targeted/modules/active/modules/cmirrord.pp':
               ['084b532fa5ccd6775c483d757bcd0920'],
           '/etc/selinux/targeted/modules/active/modules/bind.pp':
               ['5560f5706c8c8e83d8a2ac03a85b93fb'],
           '/etc/selinux/targeted/modules/active/modules/uml.pp':
               ['a0841bc9ffca619fe5d44c557b70d258'],
           '/etc/selinux/targeted/modules/active/modules/staff.pp':
               ['bdf16ee0fa0721770aa31c52e45227c3'],
           '/etc/selinux/targeted/modules/active/modules/certmaster.pp':
               ['bc589a4f0dd49a05d52b9ffda7bdd149'],
           '/etc/selinux/targeted/modules/active/modules/webalizer.pp':
               ['c99ccad469be3c901ede9da9a87e44b2'],
           '/etc/selinux/targeted/modules/active/modules/hal.pp':
               ['c75783ec2dd49d437a242e0c69c31c96'],
           '/etc/selinux/targeted/modules/active/modules/kdump.pp':
               ['d731820c7b5bb711566ea23970106b7a'],
           '/etc/selinux/targeted/modules/active/modules/firewallgui.pp':
               ['ee3522a0072989ed08f70b03f7fd69d9'],
           '/etc/selinux/targeted/modules/active/modules/tcpd.pp':
               ['b1f7db819812da14c4e836a9d9e79980'],
           '/etc/selinux/targeted/modules/active/modules/mailman.pp':
               ['4116cbe11d943a076dd06cea91993745'],
           '/etc/selinux/targeted/modules/active/modules/smartmon.pp':
               ['45d6440b436d8ac3f042e80c392dd672'],
           '/etc/selinux/targeted/modules/active/modules/smoltclient.pp':
               ['dcfd6ecd62ee7191abda39315ec6ef1b'],
           '/etc/selinux/targeted/modules/active/modules/kerberos.pp':
               ['936533081cfbe28eb9145fde86edb4f8'],
           '/etc/selinux/targeted/modules/active/modules/lockdev.pp':
               ['e2da620d3272f296dd90bff8b921d203'],
           '/etc/selinux/targeted/modules/active/modules/automount.pp':
               ['a06d3d617c6d8c29e29ce3fb0db48c9c'],
           '/etc/selinux/targeted/modules/active/modules/webadm.pp':
               ['4ac9b2f95f8d8218ec93f001995fd8ba'],
           '/etc/selinux/targeted/modules/active/modules/pyzor.pp':
               ['c2b00c08d77d7d5a8588dd82c489e354'],
           '/etc/selinux/targeted/modules/active/modules/rssh.pp':
               ['aacef6c826e9d699e84a1dd564b68105'],
           '/etc/selinux/targeted/modules/active/modules/nsplugin.pp':
               ['0c90d308f5e956900150eb6ed84b0b54'],
           '/etc/selinux/targeted/modules/active/modules/lpd.pp':
               ['5bf17a46aa2d3e2ecc0daffcf092054e'],
           '/etc/selinux/targeted/modules/active/modules/dcc.pp':
               ['84749af337d72ba6bbbe54b013c6c62c'],
           '/etc/selinux/targeted/modules/active/modules/irc.pp':
               ['42897f214251c7ca9bc04379c4abff5e'],
           '/etc/selinux/targeted/modules/active/modules/icecast.pp':
               ['962c81fc8ef5fd49c925a2249d229d1d'],
           '/etc/selinux/targeted/modules/active/modules/dnsmasq.pp':
               ['ec4a8a50eb5806e450d97a77cbe8a8b4'],
           '/etc/selinux/targeted/modules/active/modules/jabber.pp':
               ['5a528d52f7337d44bfc867333f2b1921'],
           '/etc/selinux/targeted/modules/active/modules/remotelogin.pp':
               ['68c22a0bc6e4d5031153cf10d75ba76a'],
           '/etc/selinux/targeted/modules/active/modules/boinc.pp':
               ['a70386e9ffdaccd04cbb565e6fe5c822'],
           '/etc/selinux/targeted/modules/active/modules/mrtg.pp':
               ['7e6f395e72768d350d259c15d22a1cbb'],
           '/etc/selinux/targeted/modules/active/modules/snmp.pp':
               ['fc5166e3066504601037054874fe0487'],
           '/etc/selinux/targeted/modules/active/modules/cyrus.pp':
               ['d2e792bf111ce4a6ffdb87fe11d89d16'],
           '/etc/selinux/targeted/modules/active/modules/dovecot.pp':
               ['b716de8b77f0dfeb9212d5cf36bddfa1'],
           '/etc/selinux/targeted/modules/active/modules/cdrecord.pp':
               ['24c0325480e2f1d6cf1ce31c25d5f10a'],
           '/etc/selinux/targeted/modules/active/modules/calamaris.pp':
               ['c7ec43f01369524db32249fb755f4e7f'],
           '/etc/selinux/targeted/modules/active/modules/kerneloops.pp':
               ['2493d3308dfcd34e94308af9d5c888c3'],
           '/etc/selinux/targeted/modules/active/modules/razor.pp':
               ['06425e50a31f14cec090c30e05fb9827'],
           '/etc/selinux/targeted/modules/active/netfilter_contexts':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/modules/active/seusers.final':
               ['fdf1cdf1d373e4583ca759617a1d2af3'],
           '/etc/selinux/targeted/modules/active/file_contexts.homedirs':
               ['d7c4747704e9021ec2e16c7139fedfd9'],
           '/etc/selinux/targeted/modules/active/commit_num':
               ['c08cc266624f6409b01432dac9576ab0'],
           '/etc/selinux/targeted/modules/active/policy.kern':
               ['5398a60f820803049b5bb7d90dd6196b'],
           '/etc/selinux/targeted/modules/active/homedir_template':
               ['682a31c8036aaf9cf969093d7162960a'],
           '/etc/selinux/targeted/modules/semanage.read.LOCK':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/contexts/failsafe_context':
               ['940b12538b676287b3c33e68426898ac'],
           '/etc/selinux/targeted/contexts/virtual_domain_context':
               ['1e28f1b8e58e56a64c852bd77f57d121'],
           '/etc/selinux/targeted/contexts/removable_context':
               ['e56a6b14d2bed27405d2066af463df9f'],
           '/etc/selinux/targeted/contexts/netfilter_contexts':
               ['d41d8cd98f00b204e9800998ecf8427e'],
           '/etc/selinux/targeted/contexts/userhelper_context':
               ['53441d64f9bc6337e3aac33f05d0954c'],
           '/etc/selinux/targeted/contexts/virtual_image_context':
               ['b21a69d3423d2e085d5195e25922eaa1'],
           '/etc/selinux/targeted/contexts/securetty_types':
               ['ee2445f940ed1b33e778a921cde8ad9e'],
           '/etc/selinux/targeted/contexts/default_type':
               ['d0f63fea19ee82e5f65bdbb1de899c5d'],
           '/etc/selinux/targeted/contexts/dbus_contexts':
               ['b1c42884fa5bdbde53d64cff469374fd'],
           '/etc/selinux/targeted/contexts/files/file_contexts':
               ['1622b57a3b85db3112c5f71238c68d3e'],
           '/etc/selinux/targeted/contexts/files/file_contexts.homedirs':
               ['d7c4747704e9021ec2e16c7139fedfd9'],
           '/etc/selinux/targeted/contexts/files/media':
               ['3c867677892c0a15dc0b9e9811cc2c49'],
           '/etc/selinux/targeted/contexts/initrc_context':
               ['99866a62735a38b2bf839233c1a1689d'],
           '/etc/selinux/targeted/contexts/x_contexts':
               ['9dde3f5e3ddac42b9e99a4613c972b97'],
           '/etc/selinux/targeted/contexts/customizable_types':
               ['68be87281cf3d40cb2c4606cd2b1ea2b'],
           '/etc/selinux/targeted/contexts/users/xguest_u':
               ['e26010a418df86902332c57434370246'],
           '/etc/selinux/targeted/contexts/users/unconfined_u':
               ['ee88bed48d9601ff2b11f68f97d361ac'],
           '/etc/selinux/targeted/contexts/users/staff_u':
               ['f3412f7cbf441078a9de40fcaab93254'],
           '/etc/selinux/targeted/contexts/users/root':
               ['328e08341d1ff9296573dd43c355e283'],
           '/etc/selinux/targeted/contexts/users/user_u':
               ['2fe911f440282fda0590cd99540da579'],
           '/etc/selinux/targeted/contexts/users/guest_u':
               ['61e7e7e7403b2eac30e312342e66e4cd'],
           '/etc/selinux/targeted/contexts/default_contexts':
               ['0888c75fc814058bb3c01ef58f7a1f47'],
           '/etc/selinux/targeted/policy/policy.24':
               ['5398a60f820803049b5bb7d90dd6196b'],
           '/etc/selinux/targeted/setrans.conf':
               ['ae70362b6fa2af117bd6e293ce232069'],
           '/etc/selinux/targeted/seusers':
               ['fdf1cdf1d373e4583ca759617a1d2af3'],
           '/etc/selinux/config': ['91081ef6d958e79795d0255d7c374a56'],
           '/etc/selinux/restorecond_user.conf':
               ['4e1b5b5e38c660f87d5a4f7d3a998c29'],
           '/etc/selinux/semanage.conf': ['f33b524aef1a4df2a3d0eecdda041a5c'],
           '/etc/sgml/xml-core.cat': ['bcd454c9bf55a3816a134f9766f5928f'],
           '/etc/shells': ['0e85c87e09d716ecb03624ccff511760'],
           '/etc/ssh/sshd_config': ['e24f749808133a27d94fda84a89bb27b',
                                    '8caefdd9e251b7cc1baa37874149a870',
                                    '874fafed9e745b14e5fa8ae71b82427d'],
           '/etc/sudoers': ['02f74ccbec48997f402a063a172abb48'],
           '/etc/ufw/after.rules': ['/usr/share/ufw/after.rules'],
           '/etc/ufw/after6.rules': ['/usr/share/ufw/after6.rules'],
           '/etc/ufw/before.rules': ['/usr/share/ufw/before.rules'],
           '/etc/ufw/before6.rules': ['/usr/share/ufw/before6.rules'],
           '/etc/ufw/ufw.conf': ['/usr/share/ufw/ufw.conf']}

for pathname, overrides in MD5SUMS.iteritems():
    for i in range(len(overrides)):
        if '/' != overrides[i][0]:
            continue
        try:
            overrides[i] = hashlib.md5(open(overrides[i]).read()).hexdigest()
        except IOError:
            pass


def files(b, r):
    logging.info('searching for configuration files')

    # Visit every file in `/etc` except those on the exclusion list above.
    for dirpath, dirnames, filenames in os.walk('/etc'):

        # Determine if this entire directory should be ignored by default.
        ignored = r.ignore_file(dirpath)

        # Collect up the full pathname to each file, `lstat` them all, and
        # note which ones will probably be ignored.
        files = []
        for filename in filenames:
            pathname = os.path.join(dirpath, filename)
            try:
                files.append((pathname,
                              os.lstat(pathname),
                              r.ignore_file(pathname, ignored)))
            except OSError as e:
                logging.warning('{0} caused {1} - try running as root'.
                                format(pathname, errno.errorcode[e.errno]))

        # Track the ctime of each file in this directory.  Weed out false
        # positives by ignoring files with common ctimes.
        ctimes = defaultdict(lambda: 0)

        # Map the ctimes of each directory entry that isn't being ignored.
        for pathname, s, ignored in files:
            if not ignored:
                ctimes[s.st_ctime] += 1
        for dirname in dirnames:
            try:
                ctimes[os.lstat(os.path.join(dirpath, dirname)).st_ctime] += 1
            except OSError:
                pass

        for pathname, s, ignored in files:

            # Always ignore block special files, character special files,
            # pipes, and sockets.  They end up looking like deadlocks.
            if stat.S_ISBLK(s.st_mode) \
            or stat.S_ISCHR(s.st_mode) \
            or stat.S_ISFIFO(s.st_mode) \
            or stat.S_ISSOCK(s.st_mode):
                continue

            # Make sure this pathname will actually be able to be included
            # in the blueprint.  This is a bit of a cop-out since the file
            # could be important but at least it's not a crashing bug.
            try:
                pathname = unicode(pathname)
            except UnicodeDecodeError:
                logging.warning('{0} not UTF-8 - skipping it'.
                                format(repr(pathname)[1:-1]))
                continue

            # Ignore ignored files and files that share their ctime with other
            # files in the directory.  This is a very strong indication that
            # the file is original to the system and should be ignored.
            if ignored \
            or 1 < ctimes[s.st_ctime] and r.ignore_file(pathname, True):
                continue

            # Check for a Mustache template and an optional shell script
            # that templatize this file.
            try:
                template = open(
                    '{0}.blueprint-template.mustache'.format(pathname)).read()
            except IOError:
                template = None
            try:
                data = open(
                    '{0}.blueprint-template.sh'.format(pathname)).read()
            except IOError:
                data = None

            # The content is used even for symbolic links to determine whether
            # it has changed from the packaged version.
            try:
                content = open(pathname).read()
            except IOError:
                #logging.warning('{0} not readable'.format(pathname))
                continue

            # Ignore files that are unchanged from their packaged version.
            if _unchanged(pathname, content, r):
                continue

            # Resolve the rest of the file's metadata from the
            # `/etc/passwd` and `/etc/group` databases.
            try:
                pw = pwd.getpwuid(s.st_uid)
                owner = pw.pw_name
            except KeyError:
                owner = s.st_uid
            try:
                gr = grp.getgrgid(s.st_gid)
                group = gr.gr_name
            except KeyError:
                group = s.st_gid
            mode = '{0:o}'.format(s.st_mode)

            # A symbolic link's content is the link target.
            if stat.S_ISLNK(s.st_mode):
                content = os.readlink(pathname)

                # Ignore symbolic links providing backwards compatibility
                # between SystemV init and Upstart.
                if '/lib/init/upstart-job' == content:
                    continue

                # Ignore symbolic links into the Debian alternatives system.
                # These are almost certainly managed by packages.
                if content.startswith('/etc/alternatives/'):
                    continue

                b.add_file(pathname,
                           content=content,
                           encoding='plain',
                           group=group,
                           mode=mode,
                           owner=owner)

            # A regular file is stored as plain text only if it is valid
            # UTF-8, which is required for JSON serialization.
            else:
                kwargs = dict(group=group,
                              mode=mode,
                              owner=owner)
                try:
                    if template:
                        if data:
                            kwargs['data'] = data.decode('utf_8')
                        kwargs['template'] = template.decode('utf_8')
                    else:
                        kwargs['content'] = content.decode('utf_8')
                    kwargs['encoding'] = 'plain'
                except UnicodeDecodeError:
                    if template:
                        if data:
                            kwargs['data'] = base64.b64encode(data)
                        kwargs['template'] = base64.b64encode(template)
                    else:
                        kwargs['content'] = base64.b64encode(content)
                    kwargs['encoding'] = 'base64'
                b.add_file(pathname, **kwargs)

            # If this file is a service init script or config , create a
            # service resource.
            try:
                manager, service = util.parse_service(pathname)
                if not r.ignore_service(manager, service):
                    b.add_service(manager, service)
                    b.add_service_package(manager,
                                          service,
                                          'apt',
                                          *_dpkg_query_S(pathname))
                    b.add_service_package(manager,
                                          service,
                                          'yum',
                                          *_rpm_qf(pathname))
            except ValueError:
                pass


def _dpkg_query_S(pathname):
    """
    Return a list of package names that contain `pathname` or `[]`.  This
    really can be a list thanks to `dpkg-divert`(1).
    """

    # Cache the pathname-to-package mapping.
    if not hasattr(_dpkg_query_S, '_cache'):
        _dpkg_query_S._cache = defaultdict(set)
        cache_ref = _dpkg_query_S._cache
        for listname in glob.iglob('/var/lib/dpkg/info/*.list'):
            package = os.path.splitext(os.path.basename(listname))[0]
            for line in open(listname):
                cache_ref[line.rstrip()].add(package)

    # Return the list of packages that contain this file, if any.
    if pathname in _dpkg_query_S._cache:
        return list(_dpkg_query_S._cache[pathname])

    # If `pathname` isn't in a package but is a symbolic link, see if the
    # symbolic link is in a package.  `postinst` programs commonly display
    # this pattern.
    try:
        return _dpkg_query_S(os.readlink(pathname))
    except OSError:
        pass

    return []


def _dpkg_md5sum(package, pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from a Debian package.
    """

    # Cache any MD5 sums stored in the status file.  These are typically
    # conffiles and the like.
    if not hasattr(_dpkg_md5sum, '_status_cache'):
        _dpkg_md5sum._status_cache = {}
        cache_ref = _dpkg_md5sum._status_cache
        try:
            pattern = re.compile(r'^ (\S+) ([0-9a-f]{32})')
            for line in open('/var/lib/dpkg/status'):
                match = pattern.match(line)
                if not match:
                    continue
                cache_ref[match.group(1)] = match.group(2)
        except IOError:
            pass

    # Return this file's MD5 sum, if it can be found.
    try:
        return _dpkg_md5sum._status_cache[pathname]
    except KeyError:
        pass

    # Cache the MD5 sums for files in this package.
    if not hasattr(_dpkg_md5sum, '_cache'):
        _dpkg_md5sum._cache = defaultdict(dict)
    if package not in _dpkg_md5sum._cache:
        cache_ref = _dpkg_md5sum._cache[package]
        try:
            for line in open('/var/lib/dpkg/info/{0}.md5sums'.format(package)):
                md5sum, rel_pathname = line.split(None, 1)
                cache_ref['/{0}'.format(rel_pathname.rstrip())] = md5sum
        except IOError:
            pass

    # Return this file's MD5 sum, if it can be found.
    try:
        return _dpkg_md5sum._cache[package][pathname]
    except KeyError:
        pass

    return None


def _rpm_qf(pathname):
    """
    Return a list of package names that contain `pathname` or `[]`.  RPM
    might not actually support a single pathname being claimed by more
    than one package but `dpkg` does so the interface is maintained.
    """
    try:
        p = subprocess.Popen(['rpm', '--qf=%{NAME}', '-qf', pathname],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        return []
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        return []
    return [stdout]


def _rpm_md5sum(pathname):
    """
    Find the MD5 sum of the packaged version of pathname or `None` if the
    `pathname` does not come from an RPM.
    """

    if not hasattr(_rpm_md5sum, '_cache'):
        _rpm_md5sum._cache = {}
        symlinks = []
        try:
            p = subprocess.Popen(['rpm', '-qa', '--dump'],
                                 close_fds=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            pattern = re.compile(r'^(/etc/\S+) \d+ \d+ ([0-9a-f]+) ' # No ,
                                  '(0\d+) \S+ \S+ \d \d \d (\S+)$')
            for line in p.stdout:
                match = pattern.match(line)
                if match is None:
                    continue
                if '0120777' == match.group(3):
                    symlinks.append((match.group(1), match.group(4)))
                else:
                    _rpm_md5sum._cache[match.group(1)] = match.group(2)

            # Find the MD5 sum of the targets of any symbolic links, even
            # if the target is outside of /etc.
            pattern = re.compile(r'^(/\S+) \d+ \d+ ([0-9a-f]+) ' # No ,
                                  '(0\d+) \S+ \S+ \d \d \d (\S+)$')
            for pathname, target in symlinks:
                if '/' != target[0]:
                    target = os.path.normpath(os.path.join(
                        os.path.dirname(pathname), target))
                if target in _rpm_md5sum._cache:
                    _rpm_md5sum._cache[pathname] = _rpm_md5sum._cache[target]
                else:
                    p = subprocess.Popen(['rpm', '-qf', '--dump', target],
                                         close_fds=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    for line in p.stdout:
                        match = pattern.match(line)
                        if match is not None and target == match.group(1):
                            _rpm_md5sum._cache[pathname] = match.group(2)

        except OSError:
            pass

    return _rpm_md5sum._cache.get(pathname, None)

def _unchanged(pathname, content, r):
    """
    Return `True` if a file is unchanged from its packaged version.
    """

    # Ignore files that are from the `base-files` package (which
    # doesn't include MD5 sums for every file for some reason).
    apt_packages = _dpkg_query_S(pathname)
    if 'base-files' in apt_packages:
        return True

    # Ignore files that are unchanged from their packaged version,
    # or match in MD5SUMS.
    md5sums = MD5SUMS.get(pathname, [])
    md5sums.extend([_dpkg_md5sum(package, pathname)
                    for package in apt_packages])
    md5sum = _rpm_md5sum(pathname)
    if md5sum is not None:
        md5sums.append(md5sum)
    if (hashlib.md5(content).hexdigest() in md5sums \
        or 64 in [len(md5sum or '') for md5sum in md5sums] \
           and hashlib.sha256(content).hexdigest() in md5sums) \
       and r.ignore_file(pathname, True):
        return True

    return False

########NEW FILE########
__FILENAME__ = gem
"""
Search for Ruby gems to include in the blueprint.
"""

import glob
import logging
import os
import re

from blueprint import util


def gem(b, r):
    logging.info('searching for Ruby gems')

    # Precompile a pattern for extracting the version of Ruby that was used
    # to install the gem.
    pattern = re.compile(r'gems/([^/]+)/gems')

    # Look for gems in all the typical places.  This is easier than looking
    # for `gem` commands, which may or may not be on `PATH`.
    for globname in ('/usr/lib/ruby/gems/*/gems',
                     '/usr/local/lib/ruby/gems/*/gems',
                     '/var/lib/gems/*/gems'):
        for dirname in glob.glob(globname):

            # The `ruby1.9.1` (really 1.9.2) package on Maverick begins
            # including RubyGems in the `ruby1.9.1` package and marks the
            # `rubygems1.9.1` package as virtual.  So for Maverick and
            # newer, the manager is actually `ruby1.9.1`.
            match = pattern.search(dirname)
            if '1.9.1' == match.group(1) and util.rubygems_virtual():
                manager = 'ruby{0}'.format(match.group(1))

            # Oneiric and RPM-based distros just have one RubyGems package.
            elif util.rubygems_unversioned():
                manager = 'rubygems'

            # Debian-based distros qualify the package name with the version
            # of Ruby it will use.
            else:
                manager = 'rubygems{0}'.format(match.group(1))

            for entry in os.listdir(dirname):
                try:
                    package, version = entry.rsplit('-', 1)
                except ValueError:
                    logging.warning('skipping questionably named gem {0}'.
                                    format(entry))
                    continue
                if not r.ignore_package(manager, package):
                    b.add_package(manager, package, version)

########NEW FILE########
__FILENAME__ = npm
"""
Search for npm packages to include in the blueprint.  This assumes that
Node itself is installed via Chris Lea's PPAs, either
<https://launchpad.net/~chris-lea/+archive/node.js> or
<https://launchpad.net/~chris-lea/+archive/node.js-devel>.
"""

import logging
import re
import subprocess


def npm(b, r):
    logging.info('searching for npm packages')

    # Precompile a pattern for parsing the output of `{pear,pecl} list`.
    pattern = re.compile(r'^\S+ (\S+)@(\S+)$')

    try:
        p = subprocess.Popen(['npm', 'ls', '-g'],
                             close_fds=True,
                             stdout=subprocess.PIPE)
        for line in p.stdout:
            match = pattern.match(line.rstrip())
            if match is None:
                continue
            package, version = match.group(1), match.group(2)
            if not r.ignore_package('nodejs', package):
                b.add_package('nodejs', package, version)
    except OSError:
        pass

########NEW FILE########
__FILENAME__ = php
"""
Search for PEAR/PECL packages to include in the blueprint.
"""

import logging
import re
import subprocess

from blueprint import util


def php(b, r):
    logging.info('searching for PEAR/PECL packages')

    # Precompile a pattern for parsing the output of `{pear,pecl} list`.
    pattern = re.compile(r'^([0-9a-zA-Z_]+)\s+([0-9][0-9a-zA-Z\.-]*)\s')

    # PEAR packages are managed by `php-pear` (obviously).  PECL packages
    # are managed by `php5-dev` because they require development headers
    # (less obvious but still makes sense).
    if util.lsb_release_codename() is None:
        pecl_manager = 'php-devel'
    else:
        pecl_manager = 'php5-dev'
    for manager, progname in (('php-pear', 'pear'),
                              (pecl_manager, 'pecl')):

        try:
            p = subprocess.Popen([progname, 'list'],
                                 close_fds=True, stdout=subprocess.PIPE)
        except OSError:
            continue
        for line in p.stdout:
            match = pattern.match(line)
            if match is None:
                continue
            package, version = match.group(1), match.group(2)
            if not r.ignore_package(manager, package):
                b.add_package(manager, package, version)

########NEW FILE########
__FILENAME__ = pypi
"""
Search for Python packages to include in the blueprint.
"""

import glob
import logging
import os
import re
import subprocess


# Precompile a pattern to extract the manager from a pathname.
pattern_manager = re.compile(r'lib/(python[^/]*)/(dist|site)-packages')

# Precompile patterns for differentiating between packages built by
# `easy_install` and packages built by `pip`.
pattern_egg = re.compile(r'\.egg$')
pattern_egginfo = re.compile(r'\.egg-info$')

# Precompile a pattern for extracting package names and version numbers.
pattern = re.compile(r'^([^-]+)-([^-]+).*\.egg(-info)?$')


def pypi(b, r):
    logging.info('searching for Python packages')

    # Look for packages in the typical places.  `pip` has its `freeze`
    # subcommand but there is no way but diving into the directory tree to
    # figure out what packages were `easy_install`ed.  If `VIRTUAL_ENV`
    # appears in the environment, treat the directory it names just like
    # the global package directories.
    globnames = ['/usr/lib/python*/dist-packages',
                 '/usr/lib/python*/site-packages',
                 '/usr/local/lib/python*/dist-packages',
                 '/usr/local/lib/python*/site-packages']
    virtualenv = os.getenv('VIRTUAL_ENV')
    if virtualenv is not None:
        globnames.extend(['{0}/lib/python*/dist-packages'.format(virtualenv),
                          '{0}/lib/python*/dist-packages'.format(virtualenv)])
    for globname in globnames:
        for dirname in glob.glob(globname):
            manager = pattern_manager.search(dirname).group(1)
            for entry in os.listdir(dirname):
                match = pattern.match(entry)
                if match is None:
                    continue
                package, version = match.group(1, 2)
                pathname = os.path.join(dirname, entry)

                # Symbolic links indicate this is actually a system package
                # that injects files into the PYTHONPATH.
                if os.path.islink(pathname):
                    continue

                # Assume this is a Debian-based system and let `OSError`
                # looking for `dpkg-query` prove this is RPM-based.  In
                # that case, the dependencies get a bit simpler.
                try:
                    _dpkg_query(b, r,
                                manager, package, version,
                                entry, pathname)
                except OSError:
                    try:
                        _rpm(b, r, manager, package, version, entry, pathname)
                    except OSError:
                        logging.warning('neither dpkg nor rpm found')


def _dpkg_query(b, r, manager, package, version, entry, pathname):
    """
    Resolve dependencies on Debian-based systems.
    """

    # If this Python package is actually part of a system
    # package, abandon it.
    p = subprocess.Popen(['dpkg-query', '-S', pathname],
                         close_fds=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.communicate()
    if 0 == p.returncode:
        return

    # This package was installed via `easy_install`.  Make
    # sure its version of Python is in the blueprint so it
    # can be used as a package manager.
    if pattern_egg.search(entry):
        p = subprocess.Popen(['dpkg-query', '-f=${Version}', '-W', manager],
                             close_fds=True,
                             stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if 0 != p.returncode:
            return
        versions = b.packages['apt'][manager]
        if stdout not in versions:
            versions.add(stdout)
        if not r.ignore_package(manager, package):
            b.add_package(manager, package, version)

    # This package was installed via `pip`.  Figure out how
    # `pip` was installed and use that as this package's
    # manager.
    elif pattern_egginfo.search(entry) and os.path.exists(
        os.path.join(pathname, 'installed-files.txt')):
        p = subprocess.Popen(['dpkg-query', '-W', 'python-pip'],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if 0 != p.returncode:
            if not r.ignore_package('pip', package):
                b.add_package('pip', package, version)
        else:
            if not r.ignore_package('python-pip', package):
                b.add_package('python-pip', package, version)


def _rpm(b, r, manager, package, version, entry, pathname):
    """
    Resolve dependencies on RPM-based systems.
    """

    # If this Python package is actually part of a system
    # package, abandon it.
    p = subprocess.Popen(['rpm', '-qf', pathname],
                         close_fds=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    p.communicate()
    if 0 == p.returncode:
        return

    # This package was installed via `easy_install`.  Make
    # sure Python is in the blueprint so it can be used as
    # a package manager.
    if pattern_egg.search(entry):
        p = subprocess.Popen(['rpm',
                              '--qf=%{VERSION}-%{RELEASE}.%{ARCH}',
                              '-q',
                              'python'],
                             close_fds=True,
                             stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if 0 != p.returncode:
            return
        versions = b.packages['yum']['python']
        if stdout not in versions:
            versions.add(stdout)
        if not r.ignore_package('python', package):
            b.add_package('python', package, version)

    # This package was installed via `pip`.  Figure out how
    # `pip` was installed and use that as this package's
    # manager.
    elif pattern_egginfo.search(entry) and os.path.exists(
        os.path.join(pathname, 'installed-files.txt')):
        p = subprocess.Popen(['rpm', '-q', 'python-pip'],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if 0 != p.returncode:
            if not r.ignore_package('pip', package):
                b.add_package('pip', package, version)
        else:
            if not r.ignore_package('python-pip', package):
                b.add_package('python-pip', package, version)

########NEW FILE########
__FILENAME__ = sources
"""
Search for software built from source to include in the blueprint as a tarball.
"""

import errno
import glob
import hashlib
import logging
import os
import os.path
import re
import shutil
import stat
import subprocess
import tarfile

from blueprint import context_managers
from blueprint import util


def _source(b, r, dirname, old_cwd):
    tmpname = os.path.join(os.getcwd(), dirname[1:].replace('/', '-'))

    exclude = []

    pattern_pip = re.compile(r'\.egg-info/installed-files.txt$')
    pattern_egg = re.compile(r'\.egg(?:-info)?(?:/|$)')
    pattern_pth = re.compile(
        r'lib/python[^/]+/(?:dist|site)-packages/easy-install.pth$')
    pattern_bin = re.compile(
        r'EASY-INSTALL(?:-ENTRY)?-SCRIPT|This file was generated by RubyGems')

    # Create a partial shallow copy of the directory.
    for dirpath, dirnames, filenames in os.walk(dirname):

        # Definitely ignore the shallow copy directory.
        if dirpath.startswith(tmpname):
            continue

        # Determine if this entire directory should be ignored by default.
        ignored = r.ignore_file(dirpath)

        dirpath2 = os.path.normpath(
            os.path.join(tmpname, os.path.relpath(dirpath, dirname)))

        # Create this directory in the shallow copy with matching mode, owner,
        # and owning group.  Suggest running as `root` if this doesn't work.
        os.mkdir(dirpath2)
        s = os.lstat(dirpath)
        try:
            try:
                os.lchown(dirpath2, s.st_uid, s.st_gid)
            except OverflowError:
                logging.warning('{0} has uid:gid {1}:{2} - using chown(1)'.
                                format(dirpath, s.st_uid, s.st_gid))
                p = subprocess.Popen(['chown',
                                      '{0}:{1}'.format(s.st_uid, s.st_gid),
                                      dirpath2],
                                     close_fds=True)
                p.communicate()
            os.chmod(dirpath2, s.st_mode)
        except OSError as e:
            logging.warning('{0} caused {1} - try running as root'.
                            format(dirpath, errno.errorcode[e.errno]))
            return

        for filename in filenames:
            pathname = os.path.join(dirpath, filename)

            if r.ignore_source(pathname, ignored):
                continue

            pathname2 = os.path.join(dirpath2, filename)

            # Exclude files that are part of the RubyGems package.
            for globname in (
                os.path.join('/usr/lib/ruby/gems/*/gems/rubygems-update-*/lib',
                             pathname[1:]),
                os.path.join('/var/lib/gems/*/gems/rubygems-update-*/lib',
                             pathname[1:])):
                if 0 < len(glob.glob(globname)):
                    continue

            # Remember the path to all of `pip`'s `installed_files.txt` files.
            if pattern_pip.search(pathname):
                exclude.extend([os.path.join(dirpath2, line.rstrip())
                    for line in open(pathname)])

            # Likewise remember the path to Python eggs.
            if pattern_egg.search(pathname):
                exclude.append(pathname2)

            # Exclude `easy_install`'s bookkeeping file, too.
            if pattern_pth.search(pathname):
                continue

            # Exclude executable placed by Python packages or RubyGems.
            if pathname.startswith('/usr/local/bin/'):
                try:
                    if pattern_bin.search(open(pathname).read()):
                        continue
                except IOError as e:
                    pass

            # Exclude share/applications/mimeinfo.cache, whatever that is.
            if '/usr/local/share/applications/mimeinfo.cache' == pathname:
                continue

            # Clean up dangling symbolic links.  This makes the assumption
            # that no one intends to leave dangling symbolic links hanging
            # around, which I think is a good assumption.
            s = os.lstat(pathname)
            if stat.S_ISLNK(s.st_mode):
                try:
                    os.stat(pathname)
                except OSError as e:
                    if errno.ENOENT == e.errno:
                        logging.warning('ignored dangling symbolic link {0}'.
                                        format(pathname))
                        continue

            # Hard link this file into the shallow copy.  Suggest running as
            # `root` if this doesn't work though in practice the check above
            # will have already caught this problem.
            try:
                os.link(pathname, pathname2)
            except OSError as e:
                logging.warning('{0} caused {1} - try running as root'.
                                format(pathname, errno.errorcode[e.errno]))
                return

    # Unlink files that were remembered for exclusion above.
    for pathname in exclude:
        try:
            os.unlink(pathname)
        except OSError as e:
            if e.errno not in (errno.EISDIR, errno.ENOENT):
                raise e

    # Remove empty directories.  For any that hang around, match their
    # access and modification times to the source, otherwise the hash of
    # the tarball will not be deterministic.
    for dirpath, dirnames, filenames in os.walk(tmpname, topdown=False):
        try:
            os.rmdir(dirpath)
        except OSError:
            s = os.lstat(os.path.join(dirname, os.path.relpath(dirpath,
                                                               tmpname)))
            os.utime(dirpath, (s.st_atime, s.st_mtime))

    # If the shallow copy of still exists, create a tarball named by its
    # SHA1 sum and include it in the blueprint.
    try:
        tar = tarfile.open('tmp.tar', 'w')
        tar.add(tmpname, '.')
    except OSError:
        return
    finally:
        tar.close()
    sha1 = hashlib.sha1()
    f = open('tmp.tar', 'r')
    [sha1.update(buf) for buf in iter(lambda: f.read(4096), '')]
    f.close()
    tarname = '{0}.tar'.format(sha1.hexdigest())
    shutil.move('tmp.tar', os.path.join(old_cwd, tarname))
    b.add_source(dirname, tarname)


def sources(b, r):
    logging.info('searching for software built from source')
    for pathname, negate in r['source']:
        if negate and os.path.isdir(pathname) \
        and not r.ignore_source(pathname):

            # Note before creating a working directory within pathname what
            # it's atime and mtime should be.
            s = os.lstat(pathname)

            # Create a working directory within pathname to avoid potential
            # EXDEV when creating the shallow copy and tarball.
            try:
                with context_managers.mkdtemp(pathname) as c:

                    # Restore the parent of the working directory to its
                    # original atime and mtime, as if pretending the working
                    # directory never actually existed.
                    os.utime(pathname, (s.st_atime, s.st_mtime))

                    # Create the shallow copy and possibly tarball of the
                    # relevant parts of pathname.
                    _source(b, r, pathname, c.cwd)

                # Once more restore the atime and mtime after the working
                # directory is destroyed.
                os.utime(pathname, (s.st_atime, s.st_mtime))

            # If creating the temporary directory fails, bail with a warning.
            except OSError as e:
                logging.warning('{0} caused {1} - try running as root'.
                                format(pathname, errno.errorcode[e.errno]))

    if 0 < len(b.sources):
        b.arch = util.arch()

########NEW FILE########
__FILENAME__ = yum
"""
Search for `yum` packages to include in the blueprint.
"""

import logging
import subprocess

from blueprint import util


def yum(b, r):
    logging.info('searching for Yum packages')

    # Try for the full list of packages.  If this fails, don't even
    # bother with the rest because this is probably a Debian-based
    # system.
    try:
        p = subprocess.Popen(['rpm',
                              '--qf=%{NAME}\x1E%{GROUP}\x1E%{EPOCH}' # No ,
                              '\x1E%{VERSION}-%{RELEASE}\x1E%{ARCH}\n',
                              '-qa'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError:
        return

    for line in p.stdout:
        package, group, epoch, version, arch = line.strip().split('\x1E')
        if r.ignore_package('yum', package):
            continue

        if '(none)' != epoch:
            version = '{0}:{1}'.format(epoch, version)
        if '(none)' != arch:
            version = '{0}.{1}'.format(version, arch)
        b.add_package('yum', package, version)

        # Create service resources for each service init script or config
        # in this package.
        p = subprocess.Popen(['rpm', '-ql', package],
                             close_fds=True, stdout=subprocess.PIPE)
        for line in p.stdout:
            try:
                manager, service = util.parse_service(line.rstrip())
                if not r.ignore_service(manager, service):
                    b.add_service(manager, service)
                    b.add_service_package(manager, service, 'yum', package)
            except ValueError:
                pass

########NEW FILE########
__FILENAME__ = cli
"""
Instantiate Blueprint objects for the command-line tools.  Use of these
functions outside of command-line tools is not advised, as in many cases
they exit the Python interpreter.
"""

import logging
import os
import sys

import blueprint
import context_managers
import rules


def create(options, args):
    """
    Instantiate and return a Blueprint object from either standard input or by
    reverse-engineering the system.
    """
    try:
        with context_managers.mkdtemp():

            if not os.isatty(sys.stdin.fileno()):
                try:
                    b = blueprint.Blueprint.load(sys.stdin, args[0])
                except ValueError:
                    logging.error(
                        'standard input contains invalid blueprint JSON')
                    sys.exit(1)
            else:
                b = blueprint.Blueprint.create(args[0])

            if options.subtrahend:
                logging.info('subtracting {0}'.format(options.subtrahend))
                b_s = blueprint.Blueprint.checkout(options.subtrahend)
                b = b - b_s

            b.commit(options.message or '')
            return b

    except blueprint.NameError:
        logging.error('invalid blueprint name')
        sys.exit(1)


def read(options, args):
    """
    Instantiate and return a Blueprint object from either standard input or by
    reading from the local Git repository.
    """
    try:
        name = args[0]
    except IndexError:
        name = None
    name, stdin = '-' == name and (None, True) or (name, False)
    try:
        if not os.isatty(sys.stdin.fileno()) or stdin:
            try:

                # TODO This implementation won't be able to find source
                # tarballs that should be associated with the blueprint
                # on standard input.
                return blueprint.Blueprint.load(sys.stdin, name)

            except ValueError:
                logging.error('standard input contains invalid blueprint JSON')
                sys.exit(1)
        if name is not None:
            return blueprint.Blueprint.checkout(name)
    except blueprint.NotFoundError:
        logging.error('blueprint {0} does not exist'.format(name))
        sys.exit(1)
    except blueprint.NameError:
        logging.error('invalid blueprint name {0}'.format(name))
        sys.exit(1)
    logging.error('no blueprint found on standard input')
    sys.exit(1)


def read_rules(options, args):
    """
    Instantiate and return a Blueprint object created by rules read from
    either standard input or the given pathname.
    """
    try:
        pathname = args[0]
    except IndexError:
        pathname = None
    pathname, stdin = '-' == pathname and (None, True) or (pathname, False)
    r = rules.none()
    if not os.isatty(sys.stdin.fileno()) or stdin:
        r.parse(sys.stdin)
        with context_managers.mkdtemp():
            b = blueprint.Blueprint.rules(r, 'blueprint-rendered-rules')
            b.commit(options.message or '')
            return b
    if pathname is not None:
        name, _ = os.path.splitext(os.path.basename(pathname))
        try:
            r.parse(open(pathname))
            with context_managers.mkdtemp():
                b = blueprint.Blueprint.rules(r, name)
                b.commit(options.message or '')
                return b
        except blueprint.NameError:
            logging.error('invalid blueprint name {0}'.format(name))
            sys.exit(1)
        except IOError:
            logging.error('{0} does not exist'.format(pathname))
            sys.exit(1)
    logging.error('no rules found on standard input')
    sys.exit(1)

########NEW FILE########
__FILENAME__ = context_managers
import os
import shutil
import tempfile

from blueprint import util


class cd(object):
    """
    Run in an alternative working directory in this context.
    """

    def __init__(self, new_cwd):
        self.new_cwd = new_cwd

    def __enter__(self):
        self.old_cwd = os.getcwd()
        os.chdir(self.new_cwd)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.old_cwd)


class mkdtemp(object):
    """
    Run in a temporary working directory in this context.  Remove the
    temporary directory automatically afterward.
    """

    def __init__(self, dir=None):
        self.cwd = os.getcwd()
        if dir is None:
            dir = tempfile.gettempdir()
        self.tempdir = tempfile.mkdtemp(dir=dir)
        if util.via_sudo():
            uid = int(os.environ['SUDO_UID'])
            gid = int(os.environ['SUDO_GID'])
            os.chown(self.tempdir, uid, gid)

    def __enter__(self):
        os.chdir(self.tempdir)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.cwd)
        shutil.rmtree(self.tempdir)

########NEW FILE########
__FILENAME__ = deps
import logging
import re
import subprocess


def apt(s):
    """
    Walk the dependency tree of all the packages in set s all the way to
    the leaves.  Return the set of s plus all their dependencies.
    """
    logging.debug('searching for APT dependencies')
    if not isinstance(s, set):
        s = set([s])
    tmp_s = s
    pattern_sub = re.compile(r'\([^)]+\)')
    pattern_split = re.compile(r'[,\|]')
    while 1:
        new_s = set()
        for package in tmp_s:
            p = subprocess.Popen(
                ['dpkg-query',
                 '-f', '${Pre-Depends}\n${Depends}\n${Recommends}\n',
                 '-W', package],
                close_fds=True, stdout=subprocess.PIPE)
            for line in p.stdout:
                line = line.strip()
                if '' == line:
                    continue
                for part in pattern_split.split(pattern_sub.sub('', line)):
                    new_s.add(part.strip())

        # If there is to be a next iteration, `new_s` must contain some
        # packages not yet in `s`.
        tmp_s = new_s - s
        if 0 == len(tmp_s):
            break
        s |= new_s

    return s


def yum(s):
    """
    Walk the dependency tree of all the packages in set s all the way to
    the leaves.  Return the set of s plus all their dependencies.
    """
    logging.debug('searching for Yum dependencies')

    if not hasattr(yum, '_cache'):
        yum._cache = {}
        try:
            p = subprocess.Popen(['rpm',
                                  '-qa',
                                  '--qf=%{NAME}\x1E[%{PROVIDES}\x1F]\n'],
                                 close_fds=True,
                                 stdout=subprocess.PIPE)
            for line in p.stdout:
                name, caps = line.rstrip().split('\x1E')
                yum._cache.update([(cap, name) for cap in caps.split('\x1F')])
        except OSError:
            pass

    if not isinstance(s, set):
        s = set([s])

    tmp_s = s
    while 1:
        new_s = set()
        for package in tmp_s:
            try:
                p = subprocess.Popen(['rpm', '-qR', package],
                                     close_fds=True,
                                     stdout=subprocess.PIPE)
            except OSError:
                continue
            for line in p.stdout:
                cap = line.rstrip()[0:line.find(' ')]
                if 'rpmlib' == cap[0:6]:
                    continue
                try:
                    new_s.add(yum._cache[cap])
                except KeyError:
                    try:
                        p2 = subprocess.Popen(['rpm',
                                               '-q',
                                               '--qf=%{NAME}',
                                               '--whatprovides',
                                               cap],
                                              close_fds=True,
                                              stdout=subprocess.PIPE)
                        stdout, stderr = p2.communicate()
                        yum._cache[cap] = stdout
                        new_s.add(stdout)
                    except OSError:
                        pass

        # If there is to be a next iteration, `new_s` must contain some
        # packages not yet in `s`.
        tmp_s = new_s - s
        if 0 == len(tmp_s):
            break
        s |= new_s

    return s

########NEW FILE########
__FILENAME__ = bcfg2
"""
bcfg2 configuration generator.
"""

import codecs
import logging
import os
import os.path
import platform
import re
import sys
import tarfile

try:
    import lxml.etree
except ImportError:
    print("The bcfg2 configuration generator requires the lxml python module")

# bcfg2 writes xml, shell comments not understood
DISCLAIMER = """<!--
Automatically generated by blueprint(7).
-->
"""


def bcfg2(blueprint, relaxed=False):
    """
    Generate bcfg2 code.
    """
    repo = Repo(blueprint.name, relaxed=relaxed)
    try:
        plat = platform.linux_distribution()[0].lower()
    except AttributeError:
        plat = platform.dist()[0].lower()

    def path(pathname, fprops):
        """
        Create a Path entry.

        pathname: filename
        fprops:   various file properties
        """
        repo.addpath(pathname, fprops)

    def package(manager, package, version):
        """
        Create a package entry.
        """
        repo.package(manager, package, version)

    def service(manager, service):
        """
        Create a service entry.
        """
        smap = {'centos': 'chkconfig',
                'redhat': 'chkconfig',
                'debian': 'deb',
                'ubuntu': 'deb'}
        if manager == 'sysvinit':
            stype = smap[plat]
        else:
            stype = manager

        repo.service(stype, service)

    blueprint.walk(file=path,
                   package=package,
                   service=service)

    return repo


class Repo(object):
    """
    bcfg2 repository.
    """
    def __init__(self, name, relaxed=False):
        """
        """
        self.comment = DISCLAIMER
        self.name = name
        self.relaxed = relaxed
        self.b = Bundle(name, comment=DISCLAIMER)
        self.r = Rules(name, comment=DISCLAIMER)
        self.plugs = ['Bundler', 'Rules', 'Cfg']
        self.files = []

    def addpath(self, pathname, fprops):
        """
        Add a Path entry to the specification.
        """
        self.b.path(pathname)
        if 'template' in fprops:
            logging.warning('file template {0} won\'t appear in generated '
                            'bcfg2 output'.format(pathname))
            return
        if fprops['mode'] in ['120000', '120777']:
            self.r.symlink(pathname,
                           group=fprops['group'],
                           owner=fprops['owner'],
                           to=fprops['content'])
            return
        if 'source' in fprops:
            logging.warning('Source tarballs are unsupported by bcfg2. '
                            'Please build a package for you distribution.')
        else:
            cfgent = {}

            if fprops['encoding'] == 'plain':
                cfgent['encoding'] = sys.getdefaultencoding()
                del fprops['encoding']

            cfgent['name'] = pathname
            cfgent['paranoid'] = 'False'
            cfgent['source'] = pathname[1:]
            for key, val in fprops.items():
                if key == 'mode':
                    # bcfg2 uses perms attribute
                    cfgent['perms'] = fprops['mode'][-4:]
                else:
                    cfgent[key] = val
            self.files.append(cfgent)

    def package(self, manager, package, version):
        """
        Create a package resource.
        """
        if manager == package:
            return

        if manager in ('apt', 'yum'):
            if self.relaxed or version is None:
                self.b.package(package)
                self.r.package(package, type=manager)
            else:
                self.b.package(package)
                self.r.package(package, pkgtype=manager, version=version)

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        elif 'rpm' == manager:
            self.b.rpm_package(package)
            self.r.rpm_package(package, source=version)

        # All types of gems get to have package resources.
        elif 'rubygems' == manager:
            pass  # need to build rpms
        elif re.search(r'ruby', manager) is not None:
            pass  # need to build rpms

        # these should all be Actions, i think
        else:
            self.b.action(manager(package, version, self.relaxed))
            self.r.action(manager(package, version, self.relaxed))

    def service(self, servicetype, service):
        """
        Create a Service entry.
        """
        self.b.service(service)
        self.r.service(service, servicetype)

    def writexml(self, fname, encoding='utf-8'):
        """
        Helper function for writing out xml files.
        """
        if fname.split('/')[1] == 'Bundler':
            data = lxml.etree.tostring(self.b.bundle, pretty_print=True)
        elif fname.split('/')[1] == 'Rules':
            data = lxml.etree.tostring(self.r.rules, pretty_print=True)

        fhandle = codecs.open(fname, 'w', encoding=encoding)
        fhandle.write(data)
        fhandle.close()

    def dumpf(self, gzip=False):
        """
        Generate Bcfg2 repository. The directory structure is the same
        as what is normally found in /var/lib/bcfg2.
        """
        os.mkdir(self.name)
        for plug in self.plugs:
            os.mkdir(os.path.join(self.name, plug))
            if plug in ['Bundler', 'Rules']:
                fname = os.path.join(self.name, '%s/blueprint.xml' % plug)
                self.writexml(fname)
            elif plug == 'Cfg':
                for cfgent in self.files:
                    pathdir = os.path.join(self.name, '%s/%s' %
                                           (plug, cfgent['source']))
                    os.makedirs(pathdir)
                    fname = os.path.join('%s/%s' %
                                         (pathdir,
                                          cfgent['source'].split('/')[-1]))
                    fhandle = codecs.open(fname, 'w',
                                          encoding=cfgent['encoding'])
                    try:
                        fhandle.write(cfgent['content'])
                    except UnicodeDecodeError:
                        print(cfgent['name'])
                    fhandle.close()
                    iname = os.path.join(pathdir, 'info.xml')
                    infoxml = lxml.etree.Element('FileInfo')
                    infoxml.append(\
                        lxml.etree.Element('Info',
                                           perms=cfgent['perms'],
                                           group=cfgent['group'],
                                           owner=cfgent['owner'],
                                           encoding=cfgent['encoding'],
                                           paranoid=cfgent['paranoid']))
                    data = lxml.etree.tostring(infoxml, pretty_print=True)
                    fhandle = codecs.open(iname, 'w', encoding='utf-8')
                    fhandle.write(data)
                    fhandle.close()
        if gzip:
            filename = 'bcfg2-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return self.name


class Bundle(object):
    """
    A bcfg2 Bundle contains groups of inter-dependent configuration entries,
    such as the combination of packages, configuration files, and service
    activations that comprise typical Unix daemons.

    Note that for the purposes of blueprint, all entries will be compiled
    into a single Bundle. It is up to the user to determine which groups
    of entries belong in a Bundle and rearrange them appropriately.
    """

    def __init__(self, name, comment=None):
        """
        """
        if name is None:
            self.name = 'blueprint-generated-bcfg2-bundle'
        else:
            self.name = str(name)
        self.comment = comment
        self.bundle = lxml.etree.Element('Bundle', name=self.name)

    def package(self, name):
        """
        Create a Package entry.
        """
        belem = lxml.etree.Element('Package', name=name)
        self.bundle.append(belem)

    def action(self, name):
        """
        Create an Action entry.
        """
        belem = lxml.etree.Element('Action', name="".join(name.split()))
        self.bundle.append(belem)

    def path(self, name):
        """
        Create an abstract Path entry.
        """
        belem = lxml.etree.Element('Path', name=name)
        self.bundle.append(belem)

    def service(self, name):
        """
        Create an abstract Service entry.
        """
        belem = lxml.etree.Element('Service', name=name)
        self.bundle.append(belem)


class Rules(object):
    """
    A bcfg2 Rules file contains the literal components of the
    configuration entries referenced in Bundler.
    """

    def __init__(self, name, comment=None):
        """
        """
        if name is None:
            self.name = 'blueprint-generated-bcfg2-bundle'
        else:
            self.name = str(name)
        self.comment = comment
        self.rules = lxml.etree.Element("Rules", priority='1')

    def package(self, name, pkgtype=None, **kwargs):
        """
        Create a Package entry.
        """
        # here we add the literal configuration bits
        relem = lxml.etree.Element('Package',
                                   name=name,
                                   type=pkgtype,
                                   version=kwargs['version'])
        self.rules.append(relem)

    def action(self, name):
        """
        Create an Action entry.
        """
        relem = lxml.etree.Element('Action',
                                   name="".join(name.split()),
                                   command=name,
                                   when='modified',
                                   timing='post')
        self.rules.append(relem)

    def symlink(self, name, **kwargs):
        """
        Create a Path type='symlink' entry.
        """
        etype = 'symlink'
        relem = lxml.etree.Element('Path',
                                   name=name,
                                   type=etype)
        for key, val in kwargs.items():
            relem.set(key, val)
        self.rules.append(relem)

    def service(self, name, servicetype):
        """
        Create an literal Service entry.
        """
        relem = lxml.etree.Element('Service',
                                   name=name,
                                   type=servicetype,
                                   status='on')
        self.rules.append(relem)

########NEW FILE########
__FILENAME__ = cfengine3
"""
CFEngine 3 code generator.
"""

import base64
import codecs
from collections import defaultdict
import errno
import logging
import os
import os.path
import re
import tarfile
import time
import copy

import json
from pprint import pprint

from blueprint import util
from blueprint import walk

def cfengine3(b, relaxed=False):
    """
    Generate CFEngine 3 code.
    """

    s = Sketch(b.name, policy="main.cf", comment=b.DISCLAIMER)
    # print json.dumps(b, skipkeys=True, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))

    # # Set the default `PATH` for exec resources.
    # m.add(Exec.defaults(path=os.environ['PATH']))

    def source(dirname, filename, gen_content, url):
        """
        Create file and exec resources to fetch and extract a source tarball.
        """
        s.add(Source(dirname, filename, gen_content, url));

    def file(pathname, f):
        """
        Create a file promise.
        """
        s.add(File(pathname, f))

    def package(manager, package, version):
        """
        Create a package resource.
        """
        s.add(Package(package, manager, version))

    def service(manager, service):
        """
        Create a service resource and subscribe to its dependencies.
        """
        s.add(Service(service, manager))

    b.walk(source=source,
           file=file,
           # before_packages=before_packages,
           package=package,
           service=service)

    return s

class Sketch(object):
    """
    A CFEngine 3 sketch contains any deliverables in file format.
    """

    def __init__(self, name, policy="main.cf", comment=None):
        """
        Each sketch has a name.
        """
        if name is None:
            self.name = "unknown_blueprint"
        else:
            self.name = name

        self.sketch_name = time.strftime('Blueprint::Sketch::%%s::%Y-%m-%d') % (self.name)
        self.comment = comment
        self.namespace = "blueprint_%s" % (self.name)
        self.policy = Policy(self, name=policy)
        self.dependencies = { "CFEngine::stdlib": { "version": 105 }, "CFEngine::dclib": {}, "CFEngine::Blueprint": {}, "cfengine": { "version": "3.5.0" } }
        self.contents = [ self.policy ]

    def add(self, p):
        if isinstance(p, File):
            self.contents.append(p)

        self.policy.add(p)

    def allfiles(self):
        """
        Generate the pathname and content of every file.
        """
        for item in self.contents:
            yield item.pathname, item.dirname if hasattr(item, "dirname") else "", item.content if hasattr(item, "content") else "", item.meta if hasattr(item, "meta") else {}

    def make_manifest(self):
        """
        Generate the sketch manifest.
        """
        ret = {}
        for pathname, dirname, content, meta in self.allfiles():
           ret[os.path.join(dirname, pathname[1:])] = meta

        return ret

    def make_metadata(self):
        """
        Generate the sketch manifest.
        """
        ret = { "name": self.name,
                "description": "Auto-generated sketch from Blueprint",
                "version": 1,
                "license": "unspecified",
                "tags": [ "blueprint" ],
                "depends": self.dependencies,
                "authors": [ "Your Name Here" ],
        }

        return ret

    def make_api(self):
        """
        Generate the sketch API.
        """
        return { "install": [ { "name": "runenv", "type": "environment" },
                              { "name" : "metadata", "type" : "metadata" },
                          ],
        }

    def _dump(self, w, inline=False, tab=''):
        """
        Generate the sketch index, `sketch.json`.  This will call the callable
        `w` with each line of output.  `dumps` and `dumpf` use this to
        append to a list and write to a file with the same code.

        If present, a comment is written first.  This is followed by the JSON data.

        """

        if self.comment is not None:
            comment, count = re.subn(r'#', '//', unicode(self.comment))
            w(comment)
        w(json.dumps({ "manifest": self.make_manifest(),
                       "metadata": self.make_metadata(),
                       "namespace": self.namespace,
                       "interface": [ self.policy.interface ],
                       "api": self.make_api(),
                   },
                     skipkeys=True, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': ')))

    def dumps(self):
        """
        Generate a string containing `sketch.json` only.
        """
        out = []
        self._dump(out.append, inline=True)
        return u''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing CFEngine 3 code and templates.  The directory
        structure generated is a sketch (sketch.json plus all the rest).
        """
        os.mkdir(self.name)
        filename = os.path.join(self.name, 'sketch.json')
        f = codecs.open(filename, 'w', encoding='utf-8')
        self._dump(f.write, inline=False)
        f.close()

        self.policy.make_content()

        for pathname, dirname, content, meta in self.allfiles():
            pathname = os.path.join(self.name, dirname, pathname[1:])
            try:
                os.makedirs(os.path.dirname(pathname))
            except OSError as e:
                if errno.EEXIST != e.errno:
                    raise e
            if isinstance(content, unicode):
                f = codecs.open(pathname, 'w', encoding='utf-8')
            else:
                f = open(pathname, 'w')
            f.write(content)
            f.close()
        if gzip:
            filename = 'cfengine3-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename

        return filename

class Policy(object):
    """
    CFEngine 3 policy: a container for promises.
    """
    def __init__(self, sketch, name="main.cf"):
        """
        The policy name is its filename.
        """
        self.interface = name
        self.pathname = "/" + name
        self.promises = [ ]
        self.sketch = sketch

    def add(self, promise):
        self.promises.append(promise)

    def make_vars(self):
        """
        Generate the variables as CFEngine code.

        """
        v = { "files": {}, "sources": [], "package_manager": [], "service_manager": [] }
        for promise in self.promises:
            if isinstance(promise, File):
                v['files'][promise.pathname] = copy.deepcopy(promise.meta)
                # we do not support URL sources
                v['files'][promise.pathname]['source'] = promise.dirname + promise.pathname
                # TODO: source
            elif isinstance(promise, Source):
                logging.warning('TODO: CFEngine handler for Source promise {0}, {1}'.format(promise.filename, promise.dirname))
            #     v['sources'].append(promise.filename)
            #     v['sources'].append(promise.dirname)
            #     # v['sources'].append(promise.content)
            #     v['sources'].append(promise.url)
            elif isinstance(promise, Package):
                if not promise.manager in v['package_manager']:
                    v['package_manager'].append(promise.manager)
                v.setdefault('packages_' + promise.manager, {})[promise.name] = promise.version
            elif isinstance(promise, Service):
                logging.warning('TODO: CFEngine handler for Service promise {0}, {1}'.format(promise.manager, promise.name))
                # if not promise.manager in v['service_manager']:
                #     v['service_manager'].append(promise.manager)
                # v.setdefault('services_' + promise.manager, []).append(promise.name)

        # return json.dumps(v, skipkeys=True, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
        return cfe_recurse_print(v, "      "), v

    def make_content(self):
        """
        Generate the policy as CFEngine code and put it in 'content'.

        """
        myvars, v = self.make_vars()

        ns = self.sketch.namespace
        packages = "\n".join(map(lambda x: '      "packages %s" inherit => "true", usebundle => cfdc_blueprint:packages($(runenv), "%s", $(%s_packages), "$(blueprint_packages_%s[$(%s_packages)])");' % (x, x, x, x, x),
                                 v['package_manager']))

        packvars = "\n".join(map(lambda x: '      "%s_packages" slist => getindices("blueprint_packages_%s");' % (x, x),
                                 v['package_manager']))

        self.content = """
body file control
{
      namespace => "%s";
}

bundle agent install(runenv, metadata)
{
  classes:
      "$(vars)" expression => "default:runenv_$(runenv)_$(vars)";
      "not_$(vars)" expression => "!default:runenv_$(runenv)_$(vars)";

  vars:
      "vars" slist => { "@(default:$(runenv).env_vars)" };
      "$(vars)" string => "$(default:$(runenv).$(vars))";

      "all_files" slist => getindices("blueprint_files");

%s
%s

  methods:
      "utils" usebundle => default:eu($(runenv));

    activated::
     "files" inherit => "true", usebundle => cfdc_blueprint:files($(runenv), concat(dirname($(this.promise_filename)), "/files"), $(default:eu.path_prefix), $(all_files), "%s:install.blueprint_files[$(all_files)]");
%s  
      # "sources" inherit => "true", usebundle => cfdc_blueprint:sources($(runenv), dirname($(this.promise_filename)), $(blueprint_sources));

    verbose::
      "metadata" usebundle => default:report_metadata($(this.bundle), $(metadata)),
      inherit => "true";
}
""" % (ns, myvars, packvars, ns, packages)

class Promise(object):
    """
    CFEngine 3 base promise.
    """
    pass

class Package(Promise):
    """
    CFEngine 3 packages promise.  Only one version is supported.
    """
    def __init__(self, name, manager, version):
        """
        The policy name is a filename.
        """
        self.name = name
        manager, count = re.subn(r'\W', '_', unicode(manager))
        self.manager = manager
        self.version = version


class Service(Promise):
    """
    CFEngine 3 services promise.  Not implemented.
    """
    def __init__(self, service, manager):
        """
        The service name is a unique identifier.
        """
        self.name = service
        manager, count = re.subn(r'\W', '_', unicode(manager))
        self.manager = manager

class Source(Promise):
    """
    CFEngine 3 services promise.
    """
    def __init__(self, dirname, filename, content, url):
        """
        A source->destination mapping
        """
        self.dirname = dirname
        self.filename = filename
        self.content = content
        self.url = url

class File(Promise):
    """
    CFEngine 3 files promise.
    """
    def __init__(self, filename, f):
        """
        A file spec
        """
        self.pathname = filename
        self.dirname = "files"
        self.data = f

        self.meta = { "owner": f['owner'], "group": f['group'], "perms": "" + f['mode'][-4:] }

        self.content = f['content']
        if 'base64' == f['encoding']:
            self.content = base64.b64decode(self.content)

        if 'template' in f:
            logging.warning('TODO: CFEngine file template {0}'.format(pathname))
            return

def cfe_recurse_print(d, indent):
    """
    CFEngine 3 data dump (to arrays and slists).

    Currently only supports simple lists and one or two level dicts.
    """

    quoter = lambda x: x if re.match("concat\(", x) else "'%s'" % (x)
    lines = []

    for varname, value in d.iteritems():
        if isinstance(value, dict):
            for k, v in value.iteritems():
                if isinstance(v, dict):
                    for k2, v2 in v.iteritems():
                        lines.append("%s'blueprint_%s[%s][%s]' string => %s;" % (indent, varname, k, k2, quoter(v2)))
                else:
                    lines.append("%s'blueprint_%s[%s]' string => %s;" % (indent, varname, k, quoter(v)))
        elif isinstance(value, list):
            p = map(quoter, value)
            lines.append("%s'blueprint_%s' slist => { %s };" % (indent, varname, ", ".join(p)))
        else:
            logging.warning('Unsupported data in variable %s' % (varname))

    return "\n".join(lines)

########NEW FILE########
__FILENAME__ = cfn
"""
AWS CloudFormation template generator.
"""

import codecs
import copy
import gzip as gziplib
import json
import logging
import os.path
import tarfile

from blueprint import util


def cfn(b, relaxed=False):
    b2 = copy.deepcopy(b)
    def file(pathname, f):
        if 'template' in f:
            logging.warning('file template {0} won\'t appear in generated '
                            'CloudFormation templates'.format(pathname))
            del b2.files[pathname]
    if relaxed:
        def package(manager, package, version):
            b2.packages[manager][package] = []
        b.walk(file=file, package=package)
    else:
        b.walk(file=file)
    return Template(b2)


class Template(dict):
    """
    An AWS CloudFormation template that contains a blueprint.
    """

    def __init__(self, b):
        self.b = b
        if b.name is None:
            self.name = 'blueprint-generated-cfn-template'
        else:
            self.name = b.name
        super(Template, self).__init__(json.load(open(
            os.path.join(os.path.dirname(__file__), 'cfn.json'))))
        b.normalize()
        self['Resources']['EC2Instance']['Metadata']\
            ['AWS::CloudFormation::Init']['config'] = b

    def dumps(self):
        """
        Serialize this AWS CloudFormation template to JSON in a string.
        """
        return util.json_dumps(self)

    def dumpf(self, gzip=False):
        """
        Serialize this AWS CloudFormation template to JSON in a file.
        """
        if 0 != len(self.b.sources):
            logging.warning('this blueprint contains source tarballs - '
                            'to use them with AWS CloudFormation, you must '
                            'store them online and edit the template to '
                            'reference their URLs')
        if gzip:
            filename = '{0}.json.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.json'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')
        f.write(self.dumps())
        f.close()
        return filename

########NEW FILE########
__FILENAME__ = chef
"""
Chef code generator.
"""

import base64
import codecs
import errno
import logging
import os
import os.path
import re
import tarfile

from blueprint import util
from blueprint import walk


def chef(b, relaxed=False):
    """
    Generate Chef code.
    """
    c = Cookbook(b.name, comment=b.DISCLAIMER)

    def source(dirname, filename, gen_content, url):
        """
        Create a cookbook_file and execute resource to fetch and extract
        a source tarball.
        """
        pathname = os.path.join('/tmp', filename)
        if url is not None:
            c.execute('curl -o "{0}" "{1}" || wget -O "{0}" "{1}"'.
                          format(pathname, url),
                      creates=pathname)
        elif gen_content is not None:
            c.file(pathname,
                   gen_content(),
                   owner='root',
                   group='root',
                   mode='0644',
                   backup=False,
                   source=pathname[1:])
        if '.zip' == pathname[-4:]:
            c.execute('{0}'.format(pathname),
                      command='unzip "{0}"'.format(pathname),
                      cwd=dirname)
        else:
            c.execute('{0}'.format(pathname),
                      command='tar xf "{0}"'.format(pathname),
                      cwd=dirname)

    def file(pathname, f):
        """
        Create a cookbook_file resource.
        """
        if 'template' in f:
            logging.warning('file template {0} won\'t appear in generated '
                            'Chef cookbooks'.format(pathname))
            return
        c.directory(os.path.dirname(pathname),
                    group='root',
                    mode='0755',
                    owner='root',
                    recursive=True)
        if '120000' == f['mode'] or '120777' == f['mode']:
            c.link(pathname,
                   group=f['group'],
                   owner=f['owner'],
                   to=f['content'])
            return
        if 'source' in f:
            c.remote_file(pathname,
                          backup=False,
                          group=f['group'],
                          mode=f['mode'][-4:],
                          owner=f['owner'],
                          source=f['source'])
        else:
            content = f['content']
            if 'base64' == f['encoding']:
                content = base64.b64decode(content)
            c.file(pathname,
                   content,
                   backup=False,
                   group=f['group'],
                   mode=f['mode'][-4:],
                   owner=f['owner'],
                   source=pathname[1:])

    def before_packages(manager):
        """
        Create execute resources to configure the package managers.
        """
        packages = b.packages.get(manager, [])
        if 0 == len(packages):
            return
        if 1 == len(packages) and manager in packages:
            return
        if 'apt' == manager:
            c.execute('apt-get -q update')
        elif 'yum' == manager:
            c.execute('yum makecache')

    def package(manager, package, version):
        """
        Create a package resource.
        """
        if manager == package:
            return

        if manager in ('apt', 'yum'):
            if relaxed or version is None:
                c.package(package)
            else:
                c.package(package, version=version)

            # See comments on this section in `puppet` above.
            match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
            if match is not None and util.rubygems_update():
                c.execute('/usr/bin/gem{0} install --no-rdoc --no-ri ' # No ,
                          'rubygems-update'.format(match.group(1)))
                c.execute('/usr/bin/ruby{0} ' # No ,
                          '$(PATH=$PATH:/var/lib/gems/{0}/bin ' # No ,
                          'which update_rubygems)"'.format(match.group(1)))

            if 'nodejs' == package:
                c.execute('{ ' # No ,
                          'curl http://npmjs.org/install.sh || ' # No ,
                          'wget -O- http://npmjs.org/install.sh ' # No ,
                          '} | sh',
                          creates='/usr/bin/npm')

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        elif 'rpm' == manager:
            c.rpm_package(package, source=version)

        # All types of gems get to have package resources.
        elif 'rubygems' == manager:
            if relaxed or version is None:
                c.gem_package(package)
            else:
                c.gem_package(package, version=version)
        elif re.search(r'ruby', manager) is not None:
            match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)',
                             manager)
            if relaxed or version is None:
                c.gem_package(package,
                    gem_binary='/usr/bin/gem{0}'.format(match.group(1)))
            else:
                c.gem_package(package,
                    gem_binary='/usr/bin/gem{0}'.format(match.group(1)),
                    version=version)

        # Everything else is an execute resource.
        else:
            c.execute(manager(package, version, relaxed))

    def service(manager, service):
        """
        Create a service resource and subscribe to its dependencies.
        """

        # Transform dependency list into a subscribes attribute.
        # TODO Breaks inlining.
        subscribe = []
        def service_file(m, s, pathname):
            f = b.files[pathname]
            if '120000' == f['mode'] or '120777' == f['mode']:
                subscribe.append('link[{0}]'.format(pathname))
            else:
                subscribe.append('cookbook_file[{0}]'.format(pathname))
        walk.walk_service_files(b, manager, service, service_file=service_file)
        def service_package(m, s, pm, package):
            subscribe.append('package[{0}]'.format(package))
        walk.walk_service_packages(b,
                                   manager,
                                   service,
                                   service_package=service_package)
        def service_source(m, s, dirname):
            subscribe.append('execute[{0}]'.format(b.sources[dirname]))
        walk.walk_service_sources(b,
                                  manager,
                                  service,
                                  service_source=service_source)
        subscribe = util.BareString('resources(' \
            + ', '.join([repr(s) for s in subscribe]) + ')')

        kwargs = {'action': [[':enable', ':start']],
                  'subscribes': [':restart', subscribe]}
        if 'upstart' == manager:
            kwargs['provider'] = util.BareString(
                'Chef::Provider::Service::Upstart')
        c.service(service, **kwargs)

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)

    return c


class Cookbook(object):
    """
    A cookbook is a collection of Chef resources plus the files and other
    supporting objects needed to run it.
    """

    def __init__(self, name, comment=None):
        """
        """
        if name is None:
            self.name = 'blueprint-generated-chef-cookbook'
        else:
            self.name = str(name)
        self.comment = comment
        self.resources = []
        self.files = {}

    def add(self, resource):
        """
        Resources must be added in the order they're expected to run.
        Chef does not support managing dependencies explicitly.
        """
        self.resources.append(resource)

    def directory(self, name, **kwargs):
        """
        Create a directory resource.
        """
        self.add(Resource('directory', name, **kwargs))

    def link(self, name, **kwargs):
        """
        Create a (symbolic) link resource.
        """
        self.add(Resource('link', name, **kwargs))

    def file(self, name, content, **kwargs):
        """
        Create a file or cookbook_file resource depending on whether the
        cookbook is dumped to a string or to files.
        """
        self.add(File(name, content, **kwargs))

    def remote_file(self, name, **kwargs):
        """
        Create a remote_file resource.
        """
        self.add(Resource('remote_file', name, **kwargs))

    def package(self, name, **kwargs):
        """
        Create a package resource provided by the default provider.
        """
        self.add(Resource('package', name, **kwargs))

    def rpm_package(self, name, **kwargs):
        """
        Create a package resource provided by RPM.
        """
        self.add(Resource('rpm_package', name, **kwargs))

    def gem_package(self, name, **kwargs):
        """
        Create a package resource provided by RubyGems.
        """
        self.add(Resource('gem_package', name, **kwargs))

    def execute(self, name, **kwargs):
        """
        Create an execute resource.
        """
        self.add(Resource('execute', name, **kwargs))

    def service(self, name, **kwargs):
        """
        Create a service resource.
        """
        self.add(Resource('service', name, **kwargs))

    def _dump(self, w, inline=False):
        """
        Generate Chef code.  This will call the callable `w` with each
        line of output.  `dumps` and `dumpf` use this to append to a list
        and write to a file with the same code.

        If present, a comment is written first.  Next, resources are written
        in the order they were added to the recipe.
        """
        if self.comment is not None:
            w(self.comment)
        for resource in self.resources:
            w(resource.dumps(inline))

    def dumps(self):
        """
        Generate a string containing Chef code and all file contents.
        """
        out = []
        return ''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing Chef code and templates.  The directory
        structure generated is that of a cookbook with a default recipe and
        cookbook files.
        """
        os.mkdir(self.name)
        f = codecs.open(os.path.join(self.name, 'metadata.rb'), 'w', encoding='utf-8')
        f.close()
        os.mkdir(os.path.join(self.name, 'recipes'))
        filename = os.path.join(self.name, 'recipes/default.rb')
        f = codecs.open(filename, 'w', encoding='utf-8')
        self._dump(f.write, inline=False)
        f.close()
        for resource in self.resources:
            if 'cookbook_file' != resource.type:
                continue
            pathname = os.path.join(self.name, 'files/default',
                resource.name[1:])
            try:
                os.makedirs(os.path.dirname(pathname))
            except OSError as e:
                if errno.EEXIST != e.errno:
                    raise e
            if isinstance(resource.content, unicode):
                f = codecs.open(pathname, 'w', encoding='utf-8')
            else:
                f = open(pathname, 'w')
            f.write(resource.content)
            f.close()
        if gzip:
            filename = 'chef-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return filename


class Resource(dict):
    """
    A Chef resource has a type, a name, and some parameters.  Nothing has
    to be unique as resources are dealt with in order rather than by building
    a dependency graph.

    """

    def __init__(self, type, name, **kwargs):
        """
        Don't instantiate this class directly.  Instead, use the methods made
        available in the Cookbook class.
        """
        super(Resource, self).__init__(**kwargs)
        self.type = type
        self.name = name

    @classmethod
    def _dumps(cls, value, recursive=False):
        """
        Return a value as it should be written.  If the value starts with
        a ':', it will be written as-is.  Otherwise, it will be written as
        a string.
        """
        if value is None:
            return 'nil'
        elif True == value:
            return 'true'
        elif False == value:
            return 'false'
        elif any([isinstance(value, t) for t in (int, long, float)]):
            return value
        elif 1 < len(value) and ':' == value[0]:
            return value
        elif hasattr(value, 'bare') or isinstance(value, util.BareString):
            return value
        elif isinstance(value, cls):
            return repr(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            s = ', '.join([cls._dumps(v, True) for v in value])
            if recursive:
                return '[' + s + ']'
            else:
                return s
        return repr(unicode(value).replace(u'#{', u'\\#{'))[1:]

    def dumps(self, inline=False):
        """
        Stringify differently depending on the number of options so the
        output always looks like Ruby code should look.  Parentheses are
        always employed here due to grammatical inconsistencies when using
        braces surrounding a block.
        """
        if 0 == len(self):
            return u'{0}({1})\n'.format(self.type, self._dumps(self.name))
        elif 1 == len(self):
            key, value = self.items()[0]
            return u'{0}({1}) {{ {2} {3} }}\n'.format(self.type,
                                                      self._dumps(self.name),
                                                      key,
                                                      self._dumps(value))
        else:
            out = [u'{0}({1}) do\n'.format(self.type, self._dumps(self.name))]
            for key, value in sorted(self.iteritems()):
                out.append(u'  {0} {1}\n'.format(key, self._dumps(value)))
            out.append('end\n')
            return ''.join(out)


class File(Resource):
    """
    Special Chef file or cookbook_file resource.
    """

    def __init__(self, name, content=None, **kwargs):
        """
        File resources handle their content explicitly because in some
        cases it is not written as a normal parameter.
        """
        super(File, self).__init__('file', name, **kwargs)
        self.content = content

    def dumps(self, inline=False):
        """
        Decide whether to write as a file with content or a cookbook_file
        that leaves its content to be dealt with later.
        """
        if inline:
            if self.content is not None:
                self['content'] = self.content
                del self.content
            self.type = 'file'
            del self['source']
        elif self.content is not None and 'source' in self:
            self.type = 'cookbook_file'
        return super(File, self).dumps(inline)

########NEW FILE########
__FILENAME__ = puppet
"""
Puppet code generator.
"""

import base64
import codecs
from collections import defaultdict
import errno
import logging
import os
import os.path
import re
import tarfile

from blueprint import util
from blueprint import walk


def puppet(b, relaxed=False):
    """
    Generate Puppet code.
    """
    m = Manifest(b.name, comment=b.DISCLAIMER)

    # Set the default `PATH` for exec resources.
    m.add(Exec.defaults(path=os.environ['PATH']))

    def source(dirname, filename, gen_content, url):
        """
        Create file and exec resources to fetch and extract a source tarball.
        """
        pathname = os.path.join('/tmp', filename)
        if url is not None:
            m['sources'].add(Exec(
                '/bin/sh -c \'curl -o "{0}" "{1}" || wget -O "{0}" "{1}"\''.
                    format(pathname, url),
                before=Exec.ref(dirname),
                creates=pathname))
        elif gen_content is not None:
            m['sources'].add(File(
                pathname,
                b.name,
                gen_content(),
                before=Exec.ref(dirname),
                owner='root',
                group='root',
                mode='0644',
                source='puppet:///modules/{0}{1}'.format(b.name, pathname)))
        if '.zip' == pathname[-4:]:
            m['sources'].add(Exec('unzip {0}'.format(pathname),
                                  alias=dirname,
                                  cwd=dirname))
        else:
            m['sources'].add(Exec('tar xf {0}'.format(pathname),
                                  alias=dirname,
                                  cwd=dirname))

    def file(pathname, f):
        """
        Create a file resource.
        """
        if 'template' in f:
            logging.warning('file template {0} won\'t appear in generated '
                            'Puppet modules'.format(pathname))
            return

        # Create resources for parent directories and let the
        # autorequire mechanism work out dependencies.
        dirnames = os.path.dirname(pathname).split('/')[1:]
        for i in xrange(len(dirnames)):
            m['files'].add(File(os.path.join('/', *dirnames[0:i + 1]),
                                ensure='directory'))

        # Create the actual file resource.
        if '120000' == f['mode'] or '120777' == f['mode']:
            m['files'].add(File(pathname,
                                None,
                                None,
                                owner=f['owner'],
                                group=f['group'],
                                ensure=f['content']))
            return
        if 'source' in f:
            m['files'].add(Exec(
                'curl -o "{0}" "{1}" || wget -O "{0}" "{1}"'.
                    format(pathname, f['source']),
                before=File.ref(pathname),
                creates=pathname,
                require=File.ref(os.path.dirname(pathname))))
            m['files'].add(File(pathname,
                                owner=f['owner'],
                                group=f['group'],
                                mode=f['mode'][-4:],
                                ensure='file'))
        else:
            content = f['content']
            if 'base64' == f['encoding']:
                content = base64.b64decode(content)
            m['files'].add(File(pathname,
                                b.name,
                                content,
                                owner=f['owner'],
                                group=f['group'],
                                mode=f['mode'][-4:],
                                ensure='file'))

    deps = []
    def before_packages(manager):
        """
        Create exec resources to configure the package managers.
        """
        packages = b.packages.get(manager, [])
        if 0 == len(packages):
            return
        if 1 == len(packages) and manager in packages:
            return
        if 'apt' == manager:
            m['packages'].add(Exec('apt-get -q update',
                                   before=Class.ref('apt')))
        elif 'yum' == manager:
            m['packages'].add(Exec('yum makecache', before=Class.ref('yum')))
        deps.append(manager)

    def package(manager, package, version):
        """
        Create a package resource.
        """
        ensure = 'installed' if relaxed or version is None else version

        # `apt` and `yum` are easy since they're the default for their
        # respective platforms.
        if manager in ('apt', 'yum'):
            m['packages'][manager].add(Package(package, ensure=ensure))

            # If APT is installing RubyGems, get complicated.  This would
            # make sense to do with Yum, too, but there's no consensus on
            # where, exactly, you might find RubyGems from Yum.  Going
            # the other way, it's entirely likely that doing this sort of
            # forced upgrade goes against the spirit of Blueprint itself.
            match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
            if match is not None and util.rubygems_update():
                m['packages'][manager].add(Exec('/bin/sh -c "' # No ,
                    '/usr/bin/gem{0} install --no-rdoc --no-ri ' # No ,
                    'rubygems-update; /usr/bin/ruby{0} ' # No ,
                    '$(PATH=$PATH:/var/lib/gems/{0}/bin ' # No ,
                    'which update_rubygems)"'.format(match.group(1)),
                    require=Package.ref(package)))

            if 'nodejs' == package:
                m['packages'][manager].add(Exec('/bin/sh -c " { ' # No ,
                    'curl http://npmjs.org/install.sh || ' # No ,
                    'wget -O- http://npmjs.org/install.sh ' # No ,
                    '} | sh"',
                    creates='/usr/bin/npm',
                    require=Package.ref(package)))

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        elif 'rpm' == manager:
            m['packages']['rpm'].add(Package(package,
                                             ensure='installed',
                                             provider='rpm',
                                             source=version))

        # RubyGems for Ruby 1.8 is easy, too, because Puppet has a
        # built in provider.  This is called simply "rubygems" on
        # RPM-based distros.
        elif manager in ('rubygems', 'rubygems1.8'):
            m['packages'][manager].add(Package(package,
                                               ensure=ensure,
                                               provider='gem'))

        # Other versions of RubyGems are slightly more complicated.
        elif re.search(r'ruby', manager) is not None:
            match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)',
                             manager)
            m['packages'][manager].add(Exec(
                manager(package, version, relaxed),
                creates='{0}/{1}/gems/{2}-{3}'.format(util.rubygems_path(),
                                                      match.group(1),
                                                      package,
                                                      version)))

        # Python works basically like alternative versions of Ruby
        # but follows a less predictable directory structure so the
        # directory is not known ahead of time.  This just so happens
        # to be the way everything else works, too.
        else:
            m['packages'][manager].add(Exec(manager(package,
                                                    version,
                                                    relaxed)))

    restypes = {'files': File,
                'packages': Package,
                'sources': Exec}
    def service(manager, service):
        """
        Create a service resource and subscribe to its dependencies.
        """

        # Transform dependency list into a subscribe parameter.
        subscribe = []
        def service_file(m, s, pathname):
            subscribe.append(File.ref(pathname))
        walk.walk_service_files(b, manager, service, service_file=service_file)
        def service_package(m, s, pm, package):
            subscribe.append(Package.ref(package))
        walk.walk_service_packages(b,
                                   manager,
                                   service,
                                   service_package=service_package)
        def service_source(m, s, dirname):
            subscribe.append(Exec.ref(b.sources[dirname]))
        walk.walk_service_sources(b,
                                  manager,
                                  service,
                                  service_source=service_source)

        kwargs = {'enable': True,
                  'ensure': 'running',
                  'subscribe': subscribe}
        if 'upstart' == manager:
            kwargs['provider'] = 'upstart'
        m['services'][manager].add(Service(service, **kwargs))

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)
    if 1 < len(deps):
        m['packages'].dep(*[Class.ref(dep) for dep in deps])

    # Strict ordering of classes.  Don't bother with services since
    # they manage their own dependencies.
    deps = []
    if 0 < len(b.sources):
        deps.append('sources')
    if 0 < len(b.files):
        deps.append('files')
    if 0 < len(b.packages):
        deps.append('packages')
    if 1 < len(deps):
        m.dep(*[Class.ref(dep) for dep in deps])

    return m


class Manifest(object):
    """
    A Puppet manifest contains resources and a tree of other manifests
    that may each contain resources.  Manifests are valid targets of
    dependencies and they are used heavily in the generated code to keep
    the inhumane-ness to a minimum.  A `Manifest` object generates a
    Puppet `class`.
    """

    def __init__(self, name, parent=None, comment=None):
        """
        Each class must have a name and might have a parent.  If a manifest
        has a parent, this signals it to `include` itself in the parent.
        """
        if name is None:
            self.name = 'blueprint-generated-puppet-module'
        else:
            self.name, _ = re.subn(r'\.', '--', unicode(name))
        self.parent = parent
        self.comment = comment
        self.manifests = defaultdict(dict)
        self.defaults = {}
        self.resources = defaultdict(dict)
        self.deps = []

    def __getitem__(self, name):
        """
        Manifests behave a bit like hashes in that their children can be
        traversed.  Note the children can't be assigned directly because
        that would break bidirectional parent-child relationships.
        """
        if name not in self.manifests:
            self.manifests[name] = self.__class__(name, self.name)
        return self.manifests[name]

    def add(self, resource):
        """
        Add a resource to this manifest.  Order is never important in Puppet
        since all dependencies must be declared.  Normal resources that have
        names are just added to the tree.  Resources that are declaring
        defaults for an entire type have `None` for their name, are stored
        separately, and are cumulative.
        """
        if resource.name:
            self.resources[resource.type][resource.name] = resource
        else:
            if resource.type in self.defaults:
                self.defaults[resource.type].update(resource)
            else:
                self.defaults[resource.type] = resource

    def dep(self, *args):
        """
        Declare a dependency between two or more resources.  The arguments
        will be taken from left to right to mean the left precedes the right.
        """
        self.deps.append(args)

    def files(self):
        """
        Generate the pathname and content of every file in this and any
        child manifests.
        """
        for name, resource in self.resources['file'].iteritems():
            if hasattr(resource, 'content') and resource.content is not None:
                if 'source' in resource:
                    yield name, 'files', resource.content
                else:
                    yield name, 'templates', resource.content
        for manifest in self.manifests.itervalues():
            for pathname, dirname, content in manifest.files():
                yield pathname, dirname, content

    def _dump(self, w, inline=False, tab=''):
        """
        Generate Puppet code.  This will call the callable `w` with each
        line of output.  `dumps` and `dumpf` use this to append to a list
        and write to a file with the same code.

        If present, a comment is written first.  This is followed by child
        manifests.  Within each manifest, any type defaults are written
        immediately before resources of that type.  Where possible, order
        is alphabetical.  If this manifest has a parent, the last action is
        to include this class in the parent.
        """
        if self.comment is not None:
            w(self.comment)

        # Wrap everything in a class.
        w(u'{0}class {1} {{\n'.format(tab, self.name))
        tab_extra = '{0}\t'.format(tab)

        # Type-level defaults.
        for type, resource in sorted(self.defaults.iteritems()):
            w(resource.dumps(inline, tab_extra))

        # Declare relationships between resources that appear outside the
        # scope of individual resources.
        for deps in self.deps:
            w(u'{0}{1}\n'.format(tab_extra,
                                 ' -> '.join([repr(dep) for dep in deps])))

        # Resources in this manifest.
        for type, resources in sorted(self.resources.iteritems()):
            if 1 < len(resources):
                w(u'{0}{1} {{\n'.format(tab_extra, type))
                for name, resource in sorted(resources.iteritems()):
                    resource.style = Resource.PARTIAL
                    w(resource.dumps(inline, tab_extra))
                w(u'{0}}}\n'.format(tab_extra))
            elif 1 == len(resources):
                w(resources.values()[0].dumps(inline, tab_extra))

        # Child manifests.
        for name, manifest in sorted(self.manifests.iteritems()):
            manifest._dump(w, inline, tab_extra)

        # Close the class.
        w(u'{0}}}\n'.format(tab))

        # Include the class that was just defined in its parent.  Everything
        # is included but is still namespaced.
        if self.parent is not None:
            w(u'{0}include {1}\n'.format(tab, self.name))

    def dumps(self):
        """
        Generate a string containing Puppet code and all file contents.
        This output would be suitable for use with `puppet apply` or for
        displaying an entire blueprint on a single web page.
        """
        out = []
        self._dump(out.append, inline=True)
        return u''.join(out)

    def dumpf(self, gzip=False):
        """
        Generate files containing Puppet code and templates.  The directory
        structure generated is that of a module named by the main manifest.
        """
        os.mkdir(self.name)
        os.mkdir(os.path.join(self.name, 'manifests'))
        filename = os.path.join(self.name, 'manifests/init.pp')
        f = codecs.open(filename, 'w', encoding='utf-8')
        self._dump(f.write, inline=False)
        f.close()
        for pathname, dirname, content in self.files():
            pathname = os.path.join(self.name, dirname, pathname[1:])
            try:
                os.makedirs(os.path.dirname(pathname))
            except OSError as e:
                if errno.EEXIST != e.errno:
                    raise e
            if isinstance(content, unicode):
                f = codecs.open(pathname, 'w', encoding='utf-8')
            else:
                f = open(pathname, 'w')
            f.write(content)
            f.close()
        if gzip:
            filename = 'puppet-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename
        return filename


class Resource(dict):
    """
    A Puppet resource is basically a named hash.  The name is unique to
    the Puppet catalog (which may contain any number of manifests in
    any number of modules).  The attributes that are expected vary
    by the resource's actual type.  This implementation uses the class
    name to determine the type, so do not instantiate `Resource`
    directly.
    """

    # These constants are arbitrary and only serve to control how resources
    # are written out as Puppet code.
    COMPLETE = 1
    PARTIAL = 2
    DEFAULTS = 3

    @classmethod
    def ref(cls, *args):
        """
        Reference an existing resource.  Useful for declaring dependencies
        between resources.

        It'd be great to do this with __getitem__ but that doesn't seem
        possible.
        """
        if 1 < len(args):
            return [cls.ref(arg) for arg in args]
        return cls(*args)

    @classmethod
    def defaults(cls, **kwargs):
        """
        Set defaults for a resource type.
        """
        resource = cls(None, **kwargs)
        resource.style = cls.DEFAULTS
        return resource

    def __init__(self, name, **kwargs):
        """
        A resource has a type (derived from the actual class), a name, and
        parameters, which it stores in the dictionary from which it inherits.
        By default, all resources will create COMPLETE representations.
        """
        super(Resource, self).__init__(**kwargs)
        self._type = self.__class__.__name__.lower()
        self.name = name
        self.style = self.COMPLETE

    def __repr__(self):
        """
        The string representation of a resource is the Puppet syntax for a
        reference as used when declaring dependencies.
        """
        return u'{0}[\'{1}\']'.format(self.type.capitalize(), self.name)

    @property
    def type(self):
        """
        The type of a resource is read-only and derived from the class name.
        """
        return self._type

    @classmethod
    def _dumps(cls, value, bare=True):
        """
        Return a value as it should be written.
        """
        if value is None:
            return 'undef'
        elif True == value:
            return 'true'
        elif False == value:
            return 'false'
        elif any([isinstance(value, t) for t in (int, long, float)]):
            return value
        elif bare and re.match(r'^[0-9a-zA-Z]+$', u'{0}'.format(
            value)) is not None:
            return value
        elif hasattr(value, 'bare') or isinstance(value, util.BareString):
            return value.replace(u'$', u'\\$')
        elif isinstance(value, Resource):
            return repr(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            if 1 == len(value):
                return cls._dumps(value[0])
            else:
                return '[' + ', '.join([cls._dumps(v) for v in value]) + ']'
        return repr(unicode(value).replace(u'$', u'\\$'))[1:]

    def dumps(self, inline=False, tab=''):
        """
        Generate Puppet code for this resource, returned in a string.  The
        resource's style is respected, the Puppet coding standards are
        followed, and the indentation is human-readable.
        """
        out = []

        # Begin the resource and decide tab width based on the style.
        tab_params = tab
        if self.COMPLETE == self.style:
            out.append(u'{0}{1} {{ {2}:'.format(tab,
                                                self.type,
                                                self._dumps(self.name, False)))
        elif self.PARTIAL == self.style:
            out.append(u'{0}\t{1}:'.format(tab, self._dumps(self.name, False)))
            tab_params = '{0}\t'.format(tab)
        elif self.DEFAULTS == self.style:
            out.append(u'{0}{1} {{'.format(tab, self.type.capitalize()))

        # Handle resources with parameters.
        if 0 < len(self):

            # Find the maximum parameter name length so => operators will
            # line up as coding standards dictate.
            l = max([len(key) for key in self.iterkeys()])

            # Serialize parameter values.  Certain values don't require
            # quotes.
            for key, value in sorted(self.iteritems()):
                key = u'{0}{1}'.format(key, ' ' * (l - len(key)))
                out.append(u'{0}\t{1} => {2},'.format(tab_params,
                                                      key,
                                                      self._dumps(value)))

            # Close the resource as the style dictates.
            if self.COMPLETE == self.style:
                out.append(u'{0}}}\n'.format(tab))
            elif self.PARTIAL == self.style:
                out.append(u'{0};\n'.format(out.pop()[0:-1]))
            elif self.DEFAULTS == self.style:
                out.append(u'{0}}}\n'.format(tab))

        # Handle resources without parameters.
        else:
            if self.COMPLETE == self.style:
                out.append(u'{0} }}\n'.format(out.pop()))
            elif self.PARTIAL == self.style:
                out.append(u'{0};\n'.format(out.pop()))
            elif self.DEFAULTS == self.style:
                out.append(u'{0}}}\n'.format(out.pop()))

        return '\n'.join(out)


class Class(Resource):
    """
    Puppet class resource.
    """

    def __repr__(self):
        """
        Puppet class resource names cannot contain dots due to limitations
        in the grammar.
        """
        name, count = re.subn(r'\.', '--', unicode(self.name))
        return u'{0}[\'{1}\']'.format(self.type.capitalize(), name)


class File(Resource):
    """
    Puppet file resource.
    """

    def __init__(self, name, modulename=None, content=None, **kwargs):
        """
        File resources handle their content explicitly because in some
        cases it is not written as a normal parameter.
        """
        super(File, self).__init__(name, **kwargs)
        self.modulename = modulename
        self.content = content

    def dumps(self, inline=False, tab=''):
        """
        Treat the content as a normal parameter if and only if the resource
        is being written inline.
        """
        if inline:

            # TODO Leaky abstraction.  The source attribute is perfectly
            # valid but the check here assumes it is only ever used for
            # placing source tarballs.
            if 'source' in self:
                raise ValueError("source tarballs can't be dumped as strings.")

            if getattr(self, 'content', None) is not None:
                self['content'] = self.content
                del self.content
        else:
            if self.content is not None and 'source' not in self:
                self['content'] = util.BareString(u'template(\'{0}/{1}\')'.
                                                  format(self.modulename,
                                                         self.name[1:]))
        return super(File, self).dumps(inline, tab)


class Exec(Resource):
    """
    Puppet exec resource.
    """
    pass


class Package(Resource):
    """
    Puppet package resource.
    """
    pass


class Service(Resource):
    """
    Puppet service resource.
    """
    pass

########NEW FILE########
__FILENAME__ = rules
"""
Blueprint rules generator
"""

import codecs
import gzip as gziplib


def rules(b, relaxed=False):
    """
    Generated Blueprint rules.
    """
    r = Rules(b.name, comment=b.DISCLAIMER)

    def source(dirname, filename, gen_content, url):
        r.append(':source:{0}'.format(dirname))

    def file(pathname, f):
        r.append(':file:{0}'.format(pathname))

    def package(manager, package, version):
        r.append(':package:{0}/{1}'.format(manager, package))

    def service(manager, service):
        r.append(':service:{0}/{1}'.format(manager, service))

    b.walk(source=source, file=file, package=package, service=service)

    return r


class Rules(list):

    def __init__(self, name, comment=None):
        if name is None:
            self.name = 'blueprint-generated-rules'
        else:
            self.name = name
        super(Rules, self).__init__()
        if comment is not None:
            self.append(comment)

    def dumpf(self, gzip=False):
        """
        Serialize the blueprint to a rules file.
        """
        if gzip:
            filename = '{0}.blueprint-rules.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.blueprint-rules'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')
        f.write(self.dumps())
        f.close()
        return filename

    def dumps(self):
        """
        Serialize the blueprint to rules.
        """
        return ''.join(['{0}\n'.format(item) for item in self])

########NEW FILE########
__FILENAME__ = sh
"""
Shell code generator.
"""

import codecs
from collections import defaultdict
import gzip as gziplib
import os
import os.path
import re
from shutil import copyfile
import tarfile
import unicodedata

from blueprint import git
from blueprint import util


def sh(b, relaxed=False, server='https://devstructure.com', secret=None):
    """
    Generate shell code.
    """
    s = Script(b.name, comment=b.DISCLAIMER)

    # Build an inverted index (lookup table, like in hardware, hence the name)
    # of service dependencies to services.
    lut = {'files': defaultdict(set),
           'packages': defaultdict(lambda: defaultdict(set)),
           'sources': defaultdict(set)}
    def service_file(manager, service, pathname):
        lut['files'][pathname].add((manager, service))
    def service_package(manager, service, package_manager, package):
        lut['packages'][package_manager][package].add((manager, service))
    def service_source(manager, service, dirname):
        lut['sources'][dirname].add((manager, service))
    b.walk(service_file=service_file,
           service_package=service_package,
           service_source=service_source)

    commit = git.rev_parse(b.name)
    tree = None if commit is None else git.tree(commit)
    def source(dirname, filename, gen_content, url):
        """
        Extract a source tarball.
        """
        if dirname in lut['sources']:
            s.add('MD5SUM="$(find "{0}" -printf %T@\\\\n | md5sum)"',
                  args=(dirname,))
        if url is not None:
            s.add_list(('curl -o "{0}" "{1}"',),
                       ('wget -O "{0}" "{1}"',),
                       args=(filename, url),
                       operator='||')
            if '.zip' == pathname[-4:]:
                s.add('unzip "{0}" -d "{1}"', args=(filename, dirname))
            else:
                s.add('mkdir -p "{1}" && tar xf "{0}" -C "{1}"', args=(filename, dirname))
        elif secret is not None:
            s.add_list(('curl -O "{0}/{1}/{2}/{3}"',),
                       ('wget "{0}/{1}/{2}/{3}"',),
                       args=(server, secret, b.name, filename),
                       operator='||')
            s.add('mkdir -p "{1}" && tar xf "{0}" -C "{1}"', args=(filename, dirname))
        elif gen_content is not None:
            s.add('mkdir -p "{1}" && tar xf "{0}" -C "{1}"', args=(filename, dirname))
            s.add_source(filename, git.blob(tree, filename))
        for manager, service in lut['sources'][dirname]:
            s.add_list(('[ "$MD5SUM" != "$(find "{0}" -printf %T@\\\\n '
                        '| md5sum)" ]',),
                       ('{1}=1',),
                       args=(dirname, manager.env_var(service)),
                       operator='&&')

    def file(pathname, f):
        """
        Place a file.
        """
        if pathname in lut['files']:
            s.add('MD5SUM="$(md5sum "{0}" 2>/dev/null)"', args=(pathname,))
        s.add('mkdir -p "{0}"', args=(os.path.dirname(pathname),))
        if '120000' == f['mode'] or '120777' == f['mode']:
            s.add('ln -s "{0}" "{1}"', args=(f['content'], pathname))
        else:
            if 'source' in f:
                s.add_list(('curl -o "{0}" "{1}"',),
                           ('wget -O "{0}" "{1}"',),
                           args=(pathname, f['source']),
                           operator='||')
            else:
                if 'template' in f:
                    s.templates = True
                    if 'base64' == f['encoding']:
                        commands = ('base64 --decode', 'mustache')
                    else:
                        commands = ('mustache',)
                    s.add_list(('set +x',),
                               ('. "lib/mustache.sh"',),
                               ('for F in */blueprint-template.d/*.sh',),
                               ('do',),
                               ('\t. "$F"',),
                               ('done',),
                               (f.get('data', '').rstrip(),),
                               (command(*commands,
                                        escape_stdin=True,
                                        stdin=f['template'],
                                        stdout=pathname),),
                               operator='\n',
                               wrapper='()')
                else:
                    if 'base64' == f['encoding']:
                        commands = ('base64 --decode',)
                    else:
                        commands = ('cat',)
                    s.add(*commands, stdin=f['content'], stdout=pathname)
            if 'root' != f['owner']:
                s.add('chown {0} "{1}"', args=(f['owner'], pathname))
            if 'root' != f['group']:
                s.add('chgrp {0} "{1}"', args=(f['group'], pathname))
            if '100644' != f['mode']:
                s.add('chmod {0} "{1}"', args=(f['mode'][-4:], pathname))
        for manager, service in lut['files'][pathname]:
            s.add('[ "$MD5SUM" != "$(md5sum "{0}")" ] && {1}=1',
                  args=(pathname, manager.env_var(service)))

    def before_packages(manager):
        """
        Configure the package managers.
        """
        if manager not in b.packages:
            return
        if 'apt' == manager:
            s.add('export APT_LISTBUGS_FRONTEND="none"')
            s.add('export APT_LISTCHANGES_FRONTEND="none"')
            s.add('export DEBIAN_FRONTEND="noninteractive"')
            s.add('apt-get -q update')
        elif 'yum' == manager:
            s.add('yum makecache')

    def package(manager, package, version):
        """
        Install a package.
        """
        if manager == package:
            return

        if manager in lut['packages'] and package in lut['packages'][manager]:
            s.add_list((manager.gate(package, version, relaxed),),
                       (command_list((manager.install(package,
                                                      version,
                                                      relaxed),),
                                     *[('{0}=1'.format(m.env_var(service)),)
                                       for m, service in
                                       lut['packages'][manager][package]],
                                     wrapper='{{}}'),),
                       operator='||')
        else:
            s.add(manager(package, version, relaxed))

        if manager not in ('apt', 'rpm', 'yum'):
            return

        # See comments on this section in `blueprint.frontend.puppet`.
        match = re.match(r'^rubygems(\d+\.\d+(?:\.\d+)?)$', package)
        if match is not None and util.rubygems_update():
            s.add('/usr/bin/gem{0} install --no-rdoc --no-ri rubygems-update',
                  args=(match.group(1),))
            s.add('/usr/bin/ruby{0} $(PATH=$PATH:/var/lib/gems/{0}/bin '
                  'which update_rubygems)',
                  args=(match.group(1),))

        if 'nodejs' == package:
            s.add_list(('which npm',),
                       (command_list(('curl http://npmjs.org/install.sh',),
                                     ('wget -O- http://npmjs.org/install.sh',),
                                     operator='||',
                                     wrapper='{{}}'),
                        'sh'),
                operator='||')

    def service(manager, service):
        s.add(manager(service))

    b.walk(source=source,
           file=file,
           before_packages=before_packages,
           package=package,
           service=service)

    return s


def command(*commands, **kwargs):
    commands = list(commands)
    if 'stdout' in kwargs:
        commands[-1] += ' >"{0}"'.format(kwargs['stdout'])
    if 'stdin' in kwargs:
        stdin = (kwargs['stdin'].replace(u'\\', u'\\\\').
                                 replace(u'$', u'\\$').
                                 replace(u'`', u'\\`'))
        if kwargs.get('escape_stdin', False):
            stdin = stdin.replace(u'{', u'{{').replace(u'}', u'}}')
        eof = 'EOF'
        while eof in stdin:
            eof += 'EOF'
        commands[0] += ' <<{0}'.format(eof)
        return ''.join([' | '.join(commands).format(*kwargs.get('args', ())),
                        '\n',
                        stdin,
                        '' if '' == stdin or '\n' == stdin[-1] else '\n',
                        eof])
    return ' | '.join(commands).format(*kwargs.get('args', ()))


def command_list(*commands, **kwargs):
    operator = {'&&': u' && ',
                '||': u' || ',
                '\n': u'\n',
                ';': u'; '}[kwargs.get('operator', ';')]
    wrapper = {'()': (u'(\n', u'\n)') if u'\n' == operator else (u'(', u')'),
               '{}': (u'{ ', u'; }'),
               '{{}}': (u'{{ ', u'; }}'), # Prevent double-escaping.
               '': (u'', u'')}[kwargs.get('wrapper', '')]
    return wrapper[0] \
         + operator.join([command(*c, **kwargs) for c in commands]) \
         + wrapper[-1]


class Script(object):
    """
    A script is a list of shell commands.  The pomp and circumstance is
    only necessary for providing an interface like the Puppet and Chef
    code generators.
    """

    def __init__(self, name, comment=None):
        if name is None:
            self.name = 'blueprint-generated-shell-script'
        else:
            self.name = name
        self.out = [comment if comment is not None else '',
                    'set -x\n',
                    'cd "$(dirname "$0")"\n']
        self.sources = {}
        self.templates = False

    def add(self, s='', *args, **kwargs):
        self.out.append((unicode(s) + u'\n').format(*args))
        for filename, content in kwargs.get('sources', {}).iteritems():
            self.sources[filename] = content

    def add(self, *args, **kwargs):
        """
        Add a command or pipeline to the `Script`.  Each positional `str`
        is an element in the pipeline.  The keyword argument `args`, if
        present, should contain an iterable of arguments to be substituted
        into the final pipeline by the new-style string formatting library.
        """
        self.out.append(command(*args, **kwargs))

    def add_list(self, *args, **kwargs):
        """
        Add a command or pipeline, or list of commands or pipelines, to
        the `Script`.  Each positional `str` or `tuple` argument is a
        pipeline.  The keyword argument `operator`, if present, must be
        `';'`, `'&&'`, or `'||'` to control how the pipelines are joined.
        The keyword argument `stdin`, if present, should contain a string
        that will be given heredoc-style.  The keyword argument `stdout`,
        if present, should contain a string pathname that will receive
        standard output.  The keyword argument `args`, if present, should
        contain an iterable of arguments to be substituted into the final
        pipeline by the new-style string formatting library.
        """
        self.out.append(command_list(*args, **kwargs))

    def add_source(self, filename, blob):
        """
        Add a reference to a source tarball to the `Script`.  It will be
        placed in the output directory/tarball later via `git-cat-file`(1).
        """
        self.sources[filename] = blob

    def dumps(self):
        """
        Generate a string containing shell code and all file contents.
        """
        return ''.join(self.out)

    def dumpf(self, gzip=False):
        """
        Generate a file containing shell code and all file contents.
        """

        # Open a file by the correct name, possibly with inline gzipping.
        if 0 < len(self.sources) or self.templates:
            os.mkdir(self.name)
            filename = os.path.join(self.name, 'bootstrap.sh')
            f = codecs.open(filename, 'w', encoding='utf-8')
        elif gzip:
            filename = '{0}.sh.gz'.format(self.name)
            f = gziplib.open(filename, 'w')
        else:
            filename = '{0}.sh'.format(self.name)
            f = codecs.open(filename, 'w', encoding='utf-8')

        # Bring along `mustache.sh`, the default template data files, and
        # any user-provided template data files.
        if self.templates:
            os.mkdir(os.path.join(self.name, 'etc'))
            os.mkdir(os.path.join(self.name, 'etc', 'blueprint-template.d'))
            os.mkdir(os.path.join(self.name, 'lib'))
            os.mkdir(os.path.join(self.name, 'lib', 'blueprint-template.d'))
            copyfile(os.path.join(os.path.dirname(__file__), 'mustache.sh'),
                     os.path.join(self.name, 'lib', 'mustache.sh'))
            for src, dest in [('/etc/blueprint-template.d', 'etc'),
                              (os.path.join(os.path.dirname(__file__),
                                            'blueprint-template.d'),
                               'lib')]:
                try:
                    for filename2 in os.listdir(src):
                        if filename2.endswith('.sh'):
                            copyfile(os.path.join(src, filename2),
                                     os.path.join(self.name,
                                                  dest,
                                                  'blueprint-template.d',
                                                  filename2))
                except OSError:
                    pass

        # Write the actual shell code.
        for out in self.out:
            if isinstance(out, unicode):
                out = unicodedata.normalize('NFKD', out).encode('utf-8', 'ignore')
            f.write('{0}\n'.format(out))
        f.close()

        # Bring source tarballs along.
        for filename2, blob in sorted(self.sources.iteritems()):
            git.cat_file(blob, os.path.join(self.name, filename2))

        # Possibly gzip the result.
        if gzip and (0 < len(self.sources) or self.templates):
            filename = 'sh-{0}.tar.gz'.format(self.name)
            tarball = tarfile.open(filename, 'w:gz')
            tarball.add(self.name)
            tarball.close()
            return filename

        return filename

########NEW FILE########
__FILENAME__ = git
import logging
import os
import os.path
import subprocess
import sys

from blueprint import util


class GitError(EnvironmentError):
    pass


def unroot():
    """
    Drop privileges gained through sudo(1).
    """
    if util.via_sudo():
        uid = int(os.environ['SUDO_UID'])
        gid = int(os.environ['SUDO_GID'])
        os.setgid(gid)
        os.setegid(gid)
        os.setuid(uid)
        os.seteuid(uid)


def init():
    """
    Initialize the Git repository.
    """
    dirname = repo()
    try:
        os.makedirs(dirname)
        if util.via_sudo():
            uid = int(os.environ['SUDO_UID'])
            gid = int(os.environ['SUDO_GID'])
            os.chown(dirname, uid, gid)
    except OSError:
        pass
    try:
        p = subprocess.Popen(['git',
                              '--git-dir', dirname,
                              'init',
                              '--bare',
                              '-q'],
                             close_fds=True,
                             preexec_fn=unroot,
                             stdout=sys.stderr,
                             stderr=sys.stderr)
    except OSError:
        logging.error('git not found on PATH - exiting')
        sys.exit(1)
    p.communicate()
    if 0 != p.returncode:
        #sys.exit(p.returncode)
        raise GitError(p.returncode)


def git_args():
    """
    Return the basic arguments for running Git commands against
    the blueprints repository.
    """
    return ['git', '--git-dir', repo(), '--work-tree', os.getcwd()]


def git(*args, **kwargs):
    """
    Execute a Git command.  Raises GitError on non-zero exits unless the
    raise_exc keyword argument is falsey.
    """
    try:
        p = subprocess.Popen(git_args() + list(args),
                             close_fds=True,
                             preexec_fn=unroot,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
    except OSError:
        logging.error('git not found on PATH - exiting')
        sys.exit(1)
    stdout, stderr = p.communicate(kwargs.get('stdin'))
    if 0 != p.returncode and kwargs.get('raise_exc', True):
        raise GitError(p.returncode)
    return p.returncode, stdout


def repo():
    """
    Return the full path to the Git repository.
    """
    return os.path.expandvars('$HOME/.blueprints.git')


def rev_parse(refname):
    """
    Return the referenced commit or None.
    """
    status, stdout = git('rev-parse', '-q', '--verify', refname,
                         raise_exc=False)
    if 0 != status:
        return None
    return stdout.rstrip()


def tree(commit):
    """
    Return the tree in the given commit or None.
    """
    status, stdout = git('show', '--pretty=format:%T', commit)
    if 0 != status:
        return None
    return stdout[0:40]


def ls_tree(tree, dirname=[]):
    """
    Generate all the pathnames in the given tree.
    """
    status, stdout = git('ls-tree', tree)
    for line in stdout.splitlines():
        mode, type, sha, filename = line.split()
        if 'tree' == type:
            for entry in ls_tree(sha, dirname + [filename]):
                yield entry
        else:
            yield mode, type, sha, os.path.join(*dirname + [filename])


def blob(tree, pathname):
    """
    Return the SHA of the blob by the given name in the given tree.
    """
    for mode, type, sha, pathname2 in ls_tree(tree):
        if pathname == pathname2:
            return sha
    return None


def content(blob):
    """
    Return the content of the given blob.
    """
    status, stdout = git('show', blob)
    if 0 != status:
        return None
    return stdout


def cat_file(blob, pathname=None):
    """
    If `pathname` is `None`, return an open file handle to the blob in
    Git's object store, otherwise stream the blob to `pathname`, all via
    the git-cat-file(1) command.
    """
    args = git_args() + ['cat-file', 'blob', blob]
    if pathname is None:
        return subprocess.Popen(args,
                                close_fds=True,
                                preexec_fn=unroot,
                                stdout=subprocess.PIPE).stdout
    else:
        subprocess.Popen(args,
                         close_fds=True,
                         preexec_fn=unroot,
                         stdout=open(pathname, 'w')).communicate()


def write_tree():
    status, stdout = git('write-tree')
    if 0 != status:
        return None
    return stdout.rstrip()


def commit_tree(tree, message='', parent=None):
    if parent is None:
        status, stdout = git('commit-tree', tree, stdin=message)
    else:
        status, stdout = git('commit-tree', tree, '-p', parent, stdin=message)
    if 0 != status:
        return None
    return stdout.rstrip()


def configured():
    """
    Return `True` if the author is configured in Git.  This allows Blueprint
    to bail out early for users that don't have things configured just right.
    """
    return not git('config', 'user.name', raise_exc=False)[0] \
       and not git('config', 'user.email', raise_exc=False)[0]

########NEW FILE########
__FILENAME__ = interactive
"""
Interactively walk blueprints.
"""

import git
import walk as walklib


def walk(b, choose):
    """
    Given a function for choosing a `Blueprint` object (based typically on
    the result of a `raw_input` call within the `choose` function), populate
    one or more `Blueprint`s closed into `choose`.
    """

    def file(pathname, f):
        print(pathname)
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_file(pathname, **f)

    def package(manager, package, version):
        print('{0} {1} {2}'.format(manager, package, version))
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_package(manager, package, version)

    def service(manager, service):
        print('{0} {1}'.format(manager, service))
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_service(manager, service)

        def service_file(manager, service, pathname):
            b_chosen.add_service_file(manager, service, pathname)
        walklib.walk_service_files(b_chosen,
                                   manager,
                                   service,
                                   service_file=service_file)

        def service_package(manager, service, package_manager, package):
            b_chosen.add_service_package(manager,
                                         service,
                                         package_manager,
                                         package)
        walklib.walk_service_packages(b_chosen,
                                      manager,
                                      service,
                                      service_package=service_package) 
        def service_source(manager, service, dirname):
            b_chosen.add_service_source(manager, service, dirname)
        walklib.walk_service_sources(b_chosen,
                                     manager,
                                     service,
                                     service_source=service_source)

    commit = git.rev_parse(b.name)
    tree = git.tree(commit)
    def source(dirname, filename, gen_content, url):
        if url is not None:
            print('{0} {1}'.format(dirname, url))
        elif gen_content is not None:
            blob = git.blob(tree, filename)
            git.cat_file(blob, filename)
            print('{0} {1}'.format(dirname, filename))
        b_chosen = choose()
        if b_chosen is None:
            return
        b_chosen.add_source(dirname, filename)

    b.walk(file=file, package=package, service=service, source=source)

########NEW FILE########
__FILENAME__ = http
import errno
import httplib
import socket
import urlparse

from blueprint import cfg


def _connect(server=None):
    if server is None:
        server = cfg.get('io', 'server')
    url = urlparse.urlparse(server)
    if -1 == url.netloc.find(':'):
        port = url.port or 443 if 'https' == url.scheme else 80
    else:
        port = None
    if 'https' == url.scheme:
        return httplib.HTTPSConnection(url.netloc, port)
    else:
        return httplib.HTTPConnection(url.netloc, port)


def _request(verb, path, body=None, headers={}, server=None):
    c = _connect(server)
    try:
        c.request(verb, path, body, headers)
    except socket.error as e:
        if errno.EPIPE != e.errno:
            raise e
    return c.getresponse()


def delete(path, server=None):
    return _request('DELETE', path, server=server)


def get(path, headers={}, server=None):
    c = _connect(server)
    c.request('GET', path, None, headers)
    r = c.getresponse()
    while r.status in (301, 302, 307):
       url = urlparse.urlparse(r.getheader('Location'))
       r = get(url.path,
               {'Content-Type': r.getheader('Content-Type')},
               urlparse.urlunparse((url.scheme, url.netloc, '', '', '', '')))
    return r


def post(path, body, headers={}, server=None):
    return _request('POST', path, body, headers, server)


def put(path, body, headers={}, server=None):
    return _request('PUT', path, body, headers, server)

########NEW FILE########
__FILENAME__ = backend
import boto
import boto.exception
import httplib
import socket

from blueprint import cfg
import librato
import statsd


access_key = cfg.get('s3', 'access_key')
bucket = cfg.get('s3', 'bucket')
protocol = 'https' if cfg.getboolean('s3', 'use_https') else 'http'
region = cfg.get('s3', 'region')
s3_region = 's3' if 'US' == region else 's3-{0}'.format(region)
secret_key = cfg.get('s3', 'secret_key')


def delete(key):
    """
    Remove an object from S3.  DELETE requests are free but this function
    still makes one billable request to account for freed storage.
    """
    content_length = head(key)
    if content_length is None:
        return None
    librato.count('blueprint-io-server.requests.delete')
    statsd.increment('blueprint-io-server.requests.delete')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    try:
        b.delete_key(key)
        # TODO librato.something('blueprint-io-server.storage', -content_length)
        statsd.update('blueprint-io-server.storage', -content_length)
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            boto.exception.S3ResponseError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def delete_blueprint(secret, name):
    return delete(key_for_blueprint(secret, name))


def delete_tarball(secret, name, sha):
    return delete(key_for_tarball(secret, name, sha))


def get(key):
    """
    Fetch an object from S3.  This function makes one billable request.
    """
    librato.count('blueprint-io-server.requests.get')
    statsd.increment('blueprint-io-server.requests.get')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    k = b.new_key(key)
    try:
        return k.get_contents_as_string()
    except boto.exception.S3ResponseError:
        return None
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def get_blueprint(secret, name):
    return get(key_for_blueprint(secret, name))


def get_tarball(secret, name, sha):
    return get(key_for_tarball(secret, name, sha))


def head(key):
    """
    Make a HEAD request for an object in S3.  This is needed to find the
    object's length so it can be accounted.  This function makes one
    billable request and anticipates another.
    """
    librato.count('blueprint-io-server.requests.head')
    statsd.increment('blueprint-io-server.requests.head')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    try:
        k = b.get_key(key)
        if k is None:
            return None
        return k.size
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def head_blueprint(secret, name):
    return head(key_for_blueprint(secret, name))


def head_tarball(secret, name, sha):
    return head(key_for_tarball(secret, name, sha))


def key_for_blueprint(secret, name):
    return '{0}/{1}/{2}'.format(secret,
                                name,
                                'blueprint.json')


def key_for_tarball(secret, name, sha):
    return '{0}/{1}/{2}.tar'.format(secret,
                                    name,
                                    sha)


def list(key):
    """
    List objects in S3 whose keys begin with the given prefix.  This
    function makes at least one billable request.
    """
    librato.count('blueprint-io-server.requests.list')
    statsd.increment('blueprint-io-server.requests.list')
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    return b.list(key)
    try:
        return True
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def put(key, data):
    """
    Store an object in S3.  This function makes one billable request.
    """
    librato.count('blueprint-io-server.requests.put')
    statsd.increment('blueprint-io-server.requests.put')
    # TODO librato.something('blueprint-io-server.storage', len(data))
    statsd.update('blueprint-io-server.storage', len(data))
    c = boto.connect_s3(access_key, secret_key)
    b = c.get_bucket(bucket, validate=False)
    k = b.new_key(key)
    try:
        k.set_contents_from_string(data,
                                   policy='public-read',
                                   reduced_redundancy=True)
        return True
    except (boto.exception.BotoClientError,
            boto.exception.BotoServerError,
            httplib.HTTPException,
            socket.error,
            socket.gaierror):
        return False


def put_blueprint(secret, name, data):
    return put(key_for_blueprint(secret, name), data)


def put_tarball(secret, name, sha, data):
    return put(key_for_tarball(secret, name, sha), data)


def url_for(key):
    return '{0}://{1}.{2}.amazonaws.com/{3}'.format(protocol,
                                                    bucket,
                                                    s3_region,
                                                    key)


def url_for_blueprint(secret, name):
    return url_for(key_for_blueprint(secret, name))


def url_for_tarball(secret, name, sha):
    return url_for(key_for_tarball(secret, name, sha))

########NEW FILE########
__FILENAME__ = librato
"""
Testing out Librato's metrics platform.
"""

from ConfigParser import NoOptionError, NoSectionError
import base64
import httplib
import urllib

from blueprint import cfg


try:
    token = cfg.get('librato', 'token')
    username = cfg.get('librato', 'username')
    auth = 'Basic {0}'.format(base64.b64encode('{0}:{1}'.format(username,
                                                                token)))
except (NoOptionError, NoSectionError):
    auth = None


def count(name, value=1):
    """
    Update a counter in Librato's metrics platform.
    """
    if auth is None:
        return
    conn = httplib.HTTPSConnection('metrics-api.librato.com')
    conn.request('POST',
                 '/v1/counters/{0}.json'.format(urllib.quote(name)),
                 urllib.urlencode({'value': value}),
                 {'Authorization': auth,
                  'Content-Type': 'application/x-www-form-urlencoded'})
    r = conn.getresponse()
    conn.close()

########NEW FILE########
__FILENAME__ = statsd
"""
Python interface to StatsD, cribbed from Steve Ivy <steveivy@gmail.com>'s
python_example.py in the standard distribution.
"""

from ConfigParser import NoOptionError, NoSectionError
import logging
import random
import socket
import sys

from blueprint import cfg


try:
    host, port = cfg.get('statsd', 'host'), cfg.getint('statsd', 'port')
except (NoOptionError, NoSectionError, ValueError):
    host = port = None


def timing(stat, time, sample_rate=1):
    """
    Log timing information.
    >>> statsd.timing('some.time', 500)
    """
    # TODO First positional argument may be string or list like the others.
    _send({stat: '{0}|ms'.format(time)}, sample_rate)


def increment(stats, sample_rate=1):
    """
    Increments one or more stats counters.
    >>> statsd.increment('some.int')
    >>> statsd.increment('some.int', 0.5)
    """
    update(stats, 1, sample_rate)


def decrement(stats, sample_rate=1):
    """
    Decrements one or more stats counters.
    >>> statsd.decrement('some.int')
    """
    update(stats, -1, sample_rate)


def update(stats, delta=1, sample_rate=1):
    """
    Updates one or more stats counters by arbitrary amounts.
    >>> statsd.update('some.int', 10)
    """
    if type(stats) is not list:
        stats = [stats]
    _send(dict([(stat, '{0}|c'.format(delta)) for stat in stats]), sample_rate)


def _send(data, sample_rate=1):
    """
    Squirt the metrics over UDP.
    """
    if host is None or port is None:
        return
    sampled_data = {}
    if 1 > sample_rate:
        if random.random() <= sample_rate:
            for k, v in data.iteritems():
                sampled_data[k] = '{0}|@{1}'.format(v, sample_rate)
    else:
        sampled_data = data
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for k, v in sampled_data.iteritems():
            #print('{0}:{1}'.format(k, v))
            s.sendto('{0}:{1}'.format(k, v), (host, port))
    except:
        logging.error(repr(sys.exc_info()))

########NEW FILE########
__FILENAME__ = managers
"""
Managers are callable strings that can generate the commands needed by
resources.  They're mostly useful in the context of generated shell code.
"""

import re


class PackageManager(unicode):
    """
    Package managers each have their own syntax.  All supported package
    managers are encapsulated in this manager class.
    """

    def gate(self, package, version, relaxed=False):
        """
        Return a shell command that checks for the given version of the
        given package via this package manager.  It should exit non-zero
        if the package is not in the desired state.
        """
        if version is None:
            relaxed = True

        if 'apt' == self:
            if relaxed:
                return 'dpkg-query -W {0} >/dev/null'.format(package)
            else:
                return ('[ "$(dpkg-query -f\'${{{{Version}}}}\\n\' -W {0})" '
                        '= "{1}" ]').format(package, version)

        if 'rpm' == self:
            return 'rpm -q {0} >/dev/null'.format(package)
        if 'yum' == self:
            if relaxed:
                arg = package
            else:
                match = re.match(r'^\d+:(.+)$', version)
                if match is None:
                    arg = '{0}-{1}'.format(package, version)
                else:
                    arg = '{0}-{1}'.format(package, match.group(1))
            return 'rpm -q {0} >/dev/null'.format(arg)

        if 'rubygems' == self:
            if relaxed:
                return 'gem list -i {0} >/dev/null'.format(package)
            else:
                return 'gem -i -v{1} {0} >/dev/null'.format(package, version)
        match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)', self)
        if match is not None:
            if relaxed:
                return ('gem{0} list -i {1} >/dev/null'.
                        format(match.group(1), package))
            else:
                return ('gem{0} list -i -v{2} {1} >/dev/null'.
                        format(match.group(1), package, version))

        return None

    def install(self, package, version, relaxed=False):
        """
        Return a shell command that installs the given version of the given
        package via this package manager.
        """
        if version is None:
            relaxed = True

        if 'apt' == self:
            arg = package if relaxed else '{0}={1}'.format(package, version)
            return ('apt-get -y -q -o DPkg::Options::=--force-confold '
                    'install {0}').format(arg)

        # AWS cfn-init templates may specify RPMs to be installed from URLs,
        # which are specified as versions.
        if 'rpm' == self:
            return 'rpm -U {0}'.format(version)

        if 'yum' == self:
            arg = package if relaxed else '{0}-{1}'.format(package, version)
            return 'yum -y install {0}'.format(arg)

        if 'rubygems' == self:
            if relaxed:
                return 'gem install --no-rdoc --no-ri {0}'.format(package)
            else:
                return ('gem install --no-rdoc --no-ri -v{1} {0}'.
                        format(package, version))
        match = re.match(r'^ruby(?:gems)?(\d+\.\d+(?:\.\d+)?)', self)
        if match is not None:
            if relaxed:
                return ('gem{0} install --no-rdoc --no-ri {1}'.
                        format(match.group(1), package))
            else:
                return ('gem{0} install --no-rdoc --no-ri -v{2} {1}'.
                        format(match.group(1), package, version))

        if 'python' == self:
            return 'easy_install {0}'.format(package)
        match = re.match(r'^python(\d+\.\d+)', self)
        if match is not None:
            return 'easy_install-{0} {1}'.format(match.group(1), package)
        if 'pip' == self or 'python-pip' == self:
            arg = package if relaxed else '{0}=={1}'.format(package, version)
            return 'pip install {0}'.format(arg)

        if 'php-pear' == self:
            arg = package if relaxed else '{0}-{1}'.format(package, version)
            return 'pear install {0}'.format(arg)
        if self in ('php5-dev', 'php-devel'):
            arg = package if relaxed else '{0}-{1}'.format(package, version)
            return 'pecl install {0}'.format(arg)

        if 'nodejs' == self:
            arg = package if relaxed else '{0}@{1}'.format(package, version)
            return 'npm install -g {0}'.format(arg)

        if relaxed:
            return ': unknown manager {0} for {1}'.format(self, package)
        else:
            return ': unknown manager {0} for {1} {2}'.format(self,
                                                              package,
                                                              version)

    def __call__(self, package, version, relaxed=False):
        """
        Return a shell command that checks for and possibly installs
        the given version of the given package.
        """
        gate = self.gate(package, version, relaxed)
        install = self.install(package, version, relaxed)
        if gate is None:
            return install
        return gate + ' || ' + install


class ServiceManager(unicode):
    """
    Service managers each have their own syntax.  All supported service
    managers are encapsulated in this manager class.
    """

    _env_pattern = re.compile(r'[^0-9A-Za-z]')

    def env_var(self, service):
        """
        Return the name of the environment variable being used to track the
        state of the given service.
        """
        return 'SERVICE_{0}_{1}'.format(self._env_pattern.sub('', self),
                                        self._env_pattern.sub('', service))

    def __call__(self, service):
        """
        Return a shell command that restarts the given service via this
        service manager.
        """

        if 'upstart' == self:
            return ('[ -n "${0}" ] && {{{{ restart {1} || start {1}; }}}}'.
                format(self.env_var(service), service))

        return '[ -n "${0}" ] && /etc/init.d/{1} restart'.format(
            self.env_var(service), service)

########NEW FILE########
__FILENAME__ = rules
from collections import defaultdict
import fnmatch
import glob
import json
import logging
import os
import os.path
import re
import subprocess

from blueprint import deps
from blueprint import util


# The default list of ignore patterns.  Typically, the value of each key
# will be False.  Providing True will negate the meaning of the pattern
# and cause matching files to be included in blueprints.
#
# XXX Update `blueprintignore`(5) if you make changes here.
IGNORE = {'*~': False,
          '*.blueprint-template.*': False,
          '*.dpkg-*': False,
          '/etc/.git': False,
          '/etc/.pwd.lock': False,
          '/etc/X11/default-display-manager': False,
          '/etc/adjtime': False,
          '/etc/alternatives': False,
          '/etc/apparmor': False,
          '/etc/apparmor.d': False,
          '/etc/blkid/blkid.tab': False,
          '/etc/ca-certificates.conf': False,
          '/etc/console-setup': False,

          # TODO Only if it's a symbolic link to ubuntu.
          '/etc/dpkg/origins/default': False,

          '/etc/fstab': False,
          '/etc/group-': False,
          '/etc/group': False,
          '/etc/gshadow-': False,
          '/etc/gshadow': False,
          '/etc/hostname': False,
          '/etc/init.d/.legacy-bootordering': False,
          '/etc/initramfs-tools/conf.d/resume': False,
          '/etc/ld.so.cache': False,
          '/etc/localtime': False,
          '/etc/lvm/cache': False,
          '/etc/mailcap': False,
          '/etc/mtab': False,
          '/etc/modules': False,

          # TODO Only if it's a symbolic link to /var/run/motd.
          '/etc/motd': False,

          '/etc/network/interfaces': False,
          '/etc/passwd-': False,
          '/etc/passwd': False,
          '/etc/pki/rpm-gpg': True,
          '/etc/popularity-contest.conf': False,
          '/etc/prelink.cache': False,
          '/etc/resolv.conf': False,  # Most people use the defaults.
          '/etc/rc.d': False,
          '/etc/rc0.d': False,
          '/etc/rc1.d': False,
          '/etc/rc2.d': False,
          '/etc/rc3.d': False,
          '/etc/rc4.d': False,
          '/etc/rc5.d': False,
          '/etc/rc6.d': False,
          '/etc/rcS.d': False,
          '/etc/shadow-': False,
          '/etc/shadow': False,
          '/etc/ssh/ssh_host_key*': False,
          '/etc/ssh/ssh_host_*_key*': False,
          '/etc/ssl/certs': False,
          '/etc/sysconfig/clock': False,
          '/etc/sysconfig/i18n': False,
          '/etc/sysconfig/keyboard': False,
          '/etc/sysconfig/network': False,
          '/etc/sysconfig/network-scripts': False,
          '/etc/timezone': False,
          '/etc/udev/rules.d/70-persistent-*.rules': False,
          '/etc/yum.repos.d': True}


CACHE = '/tmp/blueprintignore'


def defaults():
    """
    Parse `/etc/blueprintignore` and `~/.blueprintignore` to build the
    default `Rules` object.
    """
    r = None

    # Check for a fresh cache of the complete blueprintignore(5) rules.
    if _mtime('/etc/blueprintignore') < _mtime(CACHE) \
    and _mtime(os.path.expanduser('~/.blueprintignore')) < _mtime(CACHE) \
    and _mtime(__file__) < _mtime(CACHE):
        try:
            r = Rules(json.load(open(CACHE)))
            logging.info('using cached blueprintignore(5) rules')
            return r
        except (OSError, ValueError):
            pass

    # Cache things that are ignored by default first.
    r = Rules({
        'file': IGNORE.items(),
        'package': [('apt', package, False) for package in _apt()] +
                   [('yum', package, False) for package in _yum()],
        'service': [('sysvinit', 'skeleton', False)],
        'source': [('/', False),
                   ('/usr/local', True)],
    })

    # Cache the patterns stored in the blueprintignore files.
    logging.info('parsing blueprintignore(5) rules')
    try:
        for pathname in ['/etc/blueprintignore',
                         os.path.expanduser('~/.blueprintignore')]:
            r.parse(open(pathname), negate=True)

    except IOError:
        pass

    # Store the cache to disk.
    f = _cache_open(CACHE, 'w')
    json.dump(r, f, indent=2, sort_keys=True)
    f.close()

    return r


def none():
    """
    Build a `Rules` object that ignores every resource.
    """
    return Rules({'file': [('*', False)],
                  'package': [('*', '*', False)],
                  'service': [('*', '*', False)],
                  'source': [('/', False)]})


def _apt():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    CACHE = '/tmp/blueprint-apt-exclusions'

    # Read from a cached copy.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for APT packages to exclude')

    # Start with the root packages for the various Ubuntu installations.
    s = set(['grub-pc',
             'installation-report',
             'language-pack-en',
             'language-pack-gnome-en',
             'linux-generic-pae',
             'linux-server',
             'os-prober',
             'ubuntu-desktop',
             'ubuntu-minimal',
             'ubuntu-standard',
             'wireless-crda'])

    # Find the essential and required packages.  Every server's got 'em, no
    # one wants to muddle their blueprint with 'em.
    for field in ('Essential', 'Priority'):
        try:
            p = subprocess.Popen(['dpkg-query',
                                  '-f=${{Package}} ${{{0}}}\n'.format(field),
                                  '-W'],
                                 close_fds=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except OSError:
            _cache_open(CACHE, 'w').close()
            return s
        for line in p.stdout:
            try:
                package, property = line.rstrip().split()
                if property in ('yes', 'important', 'required', 'standard'):
                    s.add(package)
            except ValueError:
                pass

    # Walk the dependency tree all the way to the leaves.
    s = deps.apt(s)

    # Write to a cache.
    logging.info('caching excluded APT packages')
    f = _cache_open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s


def _yum():
    """
    Return the set of packages that should never appear in a blueprint because
    they're already guaranteed (to some degree) to be there.
    """

    CACHE = '/tmp/blueprint-yum-exclusions'

    # Read from a cached copy.
    try:
        return set([line.rstrip() for line in open(CACHE)])
    except IOError:
        pass
    logging.info('searching for Yum packages to exclude')

    # Start with a few groups that install common packages.
    s = set(['gpg-pubkey'])
    pattern = re.compile(r'^   (\S+)')
    try:
        p = subprocess.Popen(['yum', 'groupinfo',
                              'core','base', 'gnome-desktop'],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        _cache_open(CACHE, 'w').close()
        return s
    for line in p.stdout:
        match = pattern.match(line)
        if match is not None:
            s.add(match.group(1))

    # Walk the dependency tree all the way to the leaves.
    s = deps.yum(s)

    # Write to a cache.
    logging.info('caching excluded Yum packages')
    f = _cache_open(CACHE, 'w')
    for package in sorted(s):
        f.write('{0}\n'.format(package))
    f.close()

    return s


def _cache_open(pathname, mode):
    f = open(pathname, mode)
    if util.via_sudo():
        uid = int(os.environ['SUDO_UID'])
        gid = int(os.environ['SUDO_GID'])
        os.fchown(f.fileno(), uid, gid)
    return f


def _mtime(pathname):
    try:
        return os.stat(pathname).st_mtime
    except OSError:
        return 0


class Rules(defaultdict):
    """
    Ordered lists of rules for ignoring/unignoring particular resources.
    This is used for both `blueprintignore`(5) and `blueprint-rules`(1).
    """

    def __init__(self, *args, **kwargs):
        super(Rules, self).__init__(list, *args, **kwargs)

    def _ignore_pathname(self, restype, dirname, pathname, ignored=False):
        """
        Return `True` if the `gitignore`(5)-style `~/.blueprintignore`
        file says the given file should be ignored.  The starting state
        of the file may be overridden by setting `ignored` to `True`.
        """
        pathname = util.unicodeme(pathname)

        # Determine if the `pathname` matches the `pattern`.  `filename` is
        # given as a convenience.  See `gitignore`(5) for the rules in play.
        def match(filename, pathname, pattern):
            dir_only = '/' == pattern[-1]
            pattern = pattern.rstrip('/')
            if '/' not in pattern:
                if fnmatch.fnmatch(filename, pattern):
                    return os.path.isdir(pathname) if dir_only else True
            else:
                for p in glob.glob(os.path.join(dirname, pattern)):
                    p = util.unicodeme(p)
                    if pathname == p or pathname.startswith('{0}/'.format(p)):
                        return os.path.isdir(pathname) if dir_only else True
            return False

        # Iterate over exclusion rules until a match is found.  Then iterate
        # over inclusion rules that appear later.  If there are no matches,
        # include the file.  If only an exclusion rule matches, exclude the
        # file.  If an inclusion rule also matches, include the file.
        filename = os.path.basename(pathname)
        for pattern, negate in self[restype]:
            if ignored != negate or not match(filename, pathname, pattern):
                continue
            ignored = not ignored

        return ignored

    def ignore_file(self, pathname, ignored=False):
        """
        Return `True` if the given pathname should be ignored.
        """
        return self._ignore_pathname('file', '/etc', pathname, ignored)

    def ignore_package(self, manager, package, ignored=False):
        """
        Iterate over package exclusion rules looking for exact matches. As
        with files, search for a negated rule after finding a match. Return
        `True` to indicate the package should be ignored.
        """
        for m, p, negate in self['package']:
            if ignored != negate \
            or manager != m and '*' != m \
            or package != p and '*' != p:
                continue
            ignored = not ignored
        return ignored

    def ignore_service(self, manager, service, ignored=False):
        """
        Return `True` if a given service should be ignored.
        """
        for m, s, negate in self['service']:
            if ignored != negate \
            or manager != m and '*' != m \
            or service != s and '*' != s:
                continue
            ignored = not ignored
        return ignored

    def ignore_source(self, pathname, ignored=False):
        """
        Return `True` if the given pathname should be ignored.  Negated rules
        on directories will create new source tarballs.  Other rules will
        ignore files within those tarballs.
        """
        return self._ignore_pathname('source', '/', pathname, ignored)


    def parse(self, f, negate=False):
        """
        Parse rules from the given file-like object.  This is used both for
        `blueprintignore`(5) and for `blueprint-rules`(1).
        """
        for pattern in f:
            pattern = pattern.rstrip()

            # Comments and blank lines.
            if '' == pattern or '#' == pattern[0]:
                continue

            # Negated lines.
            if '!' == pattern[0]:
                pattern = pattern[1:]
                ignored = negate
            else:
                ignored = not negate

            # Normalize file resources, which don't need the : and type
            # qualifier, into the same format as others, like packages.
            if ':' == pattern[0]:
                try:
                    restype, pattern = pattern[1:].split(':', 2)
                except ValueError:
                    continue
            else:
                restype = 'file'

            # Ignore a package and its dependencies or unignore a single
            # package.  Empirically, the best balance of power and
            # granularity comes from this arrangement.  Take
            # build-esseantial's mutual dependence with dpkg-dev as an
            # example of why.
            if 'package' == restype:
                try:
                    manager, package = pattern.split('/')
                except ValueError:
                    logging.warning('invalid package rule "{0}"'.
                                    format(pattern))
                    continue
                self['package'].append((manager, package, ignored))
                if not ignored:
                    for dep in getattr(deps,
                                       manager,
                                       lambda(arg): [])(package):
                        self['package'].append((manager, dep, ignored))

            elif 'service' == restype:
                try:
                    manager, service = pattern.split('/')
                except ValueError:
                    logging.warning('invalid service rule "{0}"'.
                                    format(pattern))
                    continue
                self['service'].append((manager, service, ignored))

            # Ignore or unignore a file, glob, or directory tree.
            else:
                self[restype].append((pattern, ignored))

        return self

########NEW FILE########
__FILENAME__ = services
"""
Search harder for service dependencies.  The APT, Yum, and files backends
have already found the services of note but the file and package resources
which need to trigger restarts have not been fully enumerated.
"""

from collections import defaultdict
import logging
import os.path
import re
import subprocess

import util
import walk


# Pattern for matching pathnames in init scripts and such.
pattern = re.compile(r'(/[/0-9A-Za-z_.-]+)')


def services(b):
    logging.info('searching for service dependencies')

    # Command fragments for listing the files in a package.
    commands = {'apt': ['dpkg-query', '-L'],
                'yum': ['rpm', '-ql']}

    # Build a map of the directory that contains each file in the
    # blueprint to the pathname of that file.
    dirs = defaultdict(list)
    for pathname in b.files:
        dirname = os.path.dirname(pathname)
        if dirname not in ('/etc', '/etc/init', '/etc/init.d'):
            dirs[dirname].append(pathname)

    def service_file(manager, service, pathname):
        """
        Add dependencies for every pathname extracted from init scripts and
        other dependent files.
        """
        content = open(pathname).read()
        for match in pattern.finditer(content):
            if match.group(1) in b.files:
                b.add_service_file(manager, service, match.group(1))
        for dirname in b.sources.iterkeys():
            content = util.unicodeme(content)
            if dirname in content:
                b.add_service_source(manager, service, dirname)

    def service_package(manager, service, package_manager, package):
        """
        Add dependencies for every file in the blueprint that's also in
        this service's package or in a directory in this service's package.
        """
        try:
            p = subprocess.Popen(commands[package_manager] + [package],
                                 close_fds=True,
                                 stdout=subprocess.PIPE)
        except KeyError:
            return
        for line in p.stdout:
            pathname = line.rstrip()
            if pathname in b.files:
                b.add_service_file(manager, service, pathname)
            elif pathname in dirs:
                b.add_service_file(manager, service, *dirs[pathname])

    def service(manager, service):
        """
        Add extra file dependencies found in packages.  Then add extra file
        dependencies found by searching file content for pathnames.
        """
        walk.walk_service_packages(b,
                                   manager,
                                   service,
                                   service_package=service_package)
        if 'sysvinit' == manager:
            service_file(manager, service, '/etc/init.d/{0}'.format(service))
        elif 'upstart' == manager:
            service_file(manager,
                         service,
                         '/etc/init/{0}.conf'.format(service))
        walk.walk_service_files(b, manager, service, service_file=service_file)

    b.walk(service=service)

########NEW FILE########
__FILENAME__ = util
"""
Utility functions.
"""

import json
import os
import os.path
import re
import subprocess


def arch():
    """
    Return the system's architecture according to dpkg or rpm.
    """
    try:
        p = subprocess.Popen(['dpkg', '--print-architecture'],
                             close_fds=True, stdout=subprocess.PIPE)
    except OSError as e:
        p = subprocess.Popen(['rpm', '--eval', '%_arch'],
                             close_fds=True, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        return None
    return stdout.rstrip()


def lsb_release_codename():
    """
    Return the OS release's codename.
    """
    if hasattr(lsb_release_codename, '_cache'):
        return lsb_release_codename._cache
    try:
        p = subprocess.Popen(['lsb_release', '-c'], stdout=subprocess.PIPE)
    except OSError:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    stdout, stderr = p.communicate()
    if 0 != p.returncode:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    match = re.search(r'\t(\w+)$', stdout)
    if match is None:
        lsb_release_codename._cache = None
        return lsb_release_codename._cache
    lsb_release_codename._cache = match.group(1)
    return lsb_release_codename._cache


# Patterns for determining which Upstart services should be included, based
# on the events used to start them.
pattern_upstart_1 = re.compile(r'start\s+on\s+runlevel\s+\[[2345]', re.S)
pattern_upstart_2 = re.compile(r'start\s+on\s+\([^)]*(?:filesystem|filesystems|local-filesystems|mounted|net-device-up|remote-filesystems|startup|virtual-filesystems)[^)]*\)', re.S)


def parse_service(pathname):
    """
    Parse a potential service init script or config file into the
    manager and service name or raise `ValueError`.  Use the Upstart
    "start on" stanzas and SysV init's LSB headers to restrict services to
    only those that start at boot and run all the time.
    """
    dirname, basename = os.path.split(pathname)
    if '/etc/init' == dirname:
        service, ext = os.path.splitext(basename)

        # Ignore extraneous files in /etc/init.
        if '.conf' != ext:
            raise ValueError('not an Upstart config')

        # Ignore services that don't operate on the (faked) main runlevels.
        try:
            content = open(pathname).read()
        except IOError:
            raise ValueError('not a readable Upstart config')
        if not (pattern_upstart_1.search(content) \
                or pattern_upstart_2.search(content)):
            raise ValueError('not a running service')

        return ('upstart', service)
    elif '/etc/init.d' == dirname or '/etc/rc.d/init.d' == dirname:

        # Let Upstart handle its services.
        if os.path.islink(pathname) \
            and '/lib/init/upstart-job' == os.readlink(pathname):
            raise ValueError('proxy for an Upstart config')

        # Ignore services that don't operate on the main runlevels.
        try:
            content = open(pathname).read()
        except IOError:
            raise ValueError('not a readable SysV init script')
        if not re.search(r'(?:Default-Start|chkconfig):\s*[2345]', content):
            raise ValueError('not a running service')

        return ('sysvinit', basename)
    else:
        raise ValueError('not a service')


def rubygems_unversioned():
    """
    Determine whether RubyGems is suffixed by the Ruby language version.
    It ceased to be on Oneiric.  It always has been on RPM-based distros.
    """
    codename = lsb_release_codename()
    return codename is None or codename[0] >= 'o'


def rubygems_update():
    """
    Determine whether the `rubygems-update` gem is needed.  It is needed
    on Lucid and older systems.
    """
    codename = lsb_release_codename()
    return codename is not None and codename[0] < 'm'


def rubygems_virtual():
    """
    Determine whether RubyGems is baked into the Ruby 1.9 distribution.
    It is on Maverick and newer systems.
    """
    codename = lsb_release_codename()
    return codename is not None and codename[0] >= 'm'


def rubygems_path():
    """
    Determine based on the OS release where RubyGems will install gems.
    """
    if lsb_release_codename() is None or rubygems_update():
        return '/usr/lib/ruby/gems'
    return '/var/lib/gems'


def via_sudo():
    """
    Return `True` if Blueprint was invoked via `sudo`(8), which indicates
    that privileges must be dropped when writing to the filesystem.
    """
    return 'SUDO_UID' in os.environ \
        and 'SUDO_GID' in os.environ \
        and 'blueprint' in os.environ.get('SUDO_COMMAND', '')


class BareString(unicode):
    """
    Strings of this type will not be quoted when written into a Puppet
    manifest or Chef cookbook.
    """
    pass


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super(JSONEncoder, self).default(o)

def json_dumps(o):
    return JSONEncoder(indent=2, sort_keys=True).encode(o)


def unicodeme(s):
    if isinstance(s, unicode):
        return s
    for encoding in ('utf_8', 'latin_1'):
        try:
            return unicode(s, encoding)
        except UnicodeDecodeError:
            pass
    # TODO Issue a warning?
    return s

########NEW FILE########
__FILENAME__ = walk
"""
Implementation of the blueprint walking algorithm from `blueprint`(5).

It's critical that this implementation function over a naive
`dict`-of-`dict`s-of-`list`s (as constructed by `json.load` and `json.loads`)
as well as the true `defaultdict`- and `set`-based structure used by
`Blueprint` objects.  This is because the walk algorithm is used to both walk
actual `Blueprint` objects and to construct Blueprint objects.
"""

import os.path
import re

import git
import managers
import util


def walk(b, **kwargs):
    """
    Walk an entire blueprint in the appropriate order, executing callbacks
    along the way.  See blueprint(5) for details on the algorithm.  The
    callbacks are passed directly from this method to the resource
    type-specific methods and are documented there.
    """
    walk_sources(b, **kwargs)
    walk_files(b, **kwargs)
    walk_packages(b, **kwargs)
    walk_services(b, **kwargs)


def walk_sources(b, **kwargs):
    """
    Walk a blueprint's source tarballs and execute callbacks.

    * `before_sources():`
      Executed before source tarballs are enumerated.
    * `source(dirname, filename, gen_content, url):`
      Executed when a source tarball is enumerated.  Either `gen_content` or
      `url` will be `None`.  `gen_content`, when not `None`, is a callable
      that will return the file's contents.
    * `after_sources():`
      Executed after source tarballs are enumerated.
    """

    kwargs.get('before_sources', lambda *args: None)()

    pattern = re.compile(r'^(?:file|ftp|https?)://', re.I)
    callable = kwargs.get('source', lambda *args: None)
    for dirname, filename in sorted(b.get('sources', {}).iteritems()):
        if pattern.match(filename) is None:
            def gen_content():

                # It's a good thing `gen_content` is never called by the
                # `Blueprint.__init__` callbacks, since this would always
                # raise `AttributeError` on the fake blueprint structure
                # used to initialize a real `Blueprint` object.
                tree = git.tree(b._commit)

                blob = git.blob(tree, filename)
                return git.content(blob)
            callable(dirname, filename, gen_content, None)
        else:
            url = filename
            filename = os.path.basename(url)
            if '' == filename:
                filename = 'blueprint-downloaded-tarball.tar.gz'
            callable(dirname, filename, None, url)

    kwargs.get('before_sources', lambda *args: None)()


def walk_files(b, **kwargs):
    """
    Walk a blueprint's files and execute callbacks.

    * `before_files():`
      Executed before files are enumerated.
    * `file(pathname, f):`
      Executed when a file is enumerated.
    * `after_files():`
      Executed after files are enumerated.
    """

    kwargs.get('before_files', lambda *args: None)()

    callable = kwargs.get('file', lambda *args: None)
    for pathname, f in sorted(b.get('files', {}).iteritems()):

        # AWS cfn-init templates may specify file content as JSON, which
        # must be converted to a string here, lest each frontend have to
        # do so.
        if 'content' in f and not isinstance(f['content'], basestring):
            f['content'] = util.json_dumps(f['content'])

        callable(pathname, f)

    kwargs.get('after_files', lambda *args: None)()


def walk_packages(b, managername=None, **kwargs):
    """
    Walk a package tree and execute callbacks along the way.  This is a bit
    like iteration but can't match the iterator protocol due to the varying
    argument lists given to each type of callback.  The available callbacks
    are:

    * `before_packages(manager):`
      Executed before a package manager's dependencies are enumerated.
    * `package(manager, package, version):`
      Executed when a package version is enumerated.
    * `after_packages(manager):`
      Executed after a package manager's dependencies are enumerated.
    """

    # Walking begins with the system package managers, `apt`, `rpm`,
    # and `yum`.
    if managername is None:
        walk_packages(b, 'apt', **kwargs)
        walk_packages(b, 'rpm', **kwargs)
        walk_packages(b, 'yum', **kwargs)
        return

    # Get the full manager from its name.
    manager = managers.PackageManager(managername)

    # Give the manager a chance to setup for its dependencies.
    kwargs.get('before_packages', lambda *args: None)(manager)

    # Each package gets its chance to take action.  Note which packages
    # are themselves managers so they may be visited recursively later.
    next_managers = []
    callable = kwargs.get('package', lambda *args: None)
    for package, versions in sorted(b.get('packages',
                                          {}).get(manager,
                                                  {}).iteritems()):
        if 0 == len(versions):
            callable(manager, package, None)
        elif isinstance(versions, basestring):
            callable(manager, package, versions)
        else:
            for version in versions:
                callable(manager, package, version)
        if managername != package and package in b.get('packages', {}):
            next_managers.append(package)

    # Give the manager a change to cleanup after itself.
    kwargs.get('after_packages', lambda *args: None)(manager)

    # Now recurse into each manager that was just installed.  Recursing
    # here is safer because there may be secondary dependencies that are
    # not expressed in the hierarchy (for example the `mysql2` gem
    # depends on `libmysqlclient-dev` in addition to its manager).
    for managername in next_managers:
        walk_packages(b, managername, **kwargs)


def walk_services(b, managername=None, **kwargs):
    """
    Walk a blueprint's services and execute callbacks.

    * `before_services(manager):`
      Executed before a service manager's dependencies are enumerated.
    * `service(manager, service):`
      Executed when a service is enumerated.
    * `after_services(manager):`
      Executed after a service manager's dependencies are enumerated.
    """

    # Unless otherwise specified, walk all service managers.
    if managername is None:
        for managername in sorted(b.get('services', {}).iterkeys()):
            walk_services(b, managername, **kwargs)
        return

    manager = managers.ServiceManager(managername)

    kwargs.get('before_services', lambda *args: None)(manager)

    callable = kwargs.get('service', lambda *args: None)
    for service, deps in sorted(b.get('services',
                                      {}).get(manager,
                                              {}).iteritems()):
        callable(manager, service)
        walk_service_files(b, manager, service, **kwargs)
        walk_service_packages(b, manager, service, **kwargs)
        walk_service_sources(b, manager, service, **kwargs)

    kwargs.get('after_services', lambda *args: None)(manager)


def walk_service_files(b, manager, servicename, **kwargs):
    """
    Walk a service's file dependencies and execute callbacks.

    * `service_file(manager, servicename, pathname):`
      Executed when a file service dependency is enumerated.
    """
    deps = b.get('services', {}).get(manager, {}).get(servicename, {})
    if 'files' not in deps:
        return
    callable = kwargs.get('service_file', lambda *args: None)
    for pathname in list(deps['files']):
        callable(manager, servicename, pathname)


def walk_service_packages(b, manager, servicename, **kwargs):
    """
    Walk a service's package dependencies and execute callbacks.

    * `service_package(manager,
                       servicename,
                       package_managername,
                       package):`
      Executed when a file service dependency is enumerated.
    """
    deps = b.get('services', {}).get(manager, {}).get(servicename, {})
    if 'packages' not in deps:
        return
    callable = kwargs.get('service_package', lambda *args: None)
    for package_managername, packages in deps['packages'].iteritems():
        for package in packages:
            callable(manager, servicename, package_managername, package)


def walk_service_sources(b, manager, servicename, **kwargs):
    """
    Walk a service's source tarball dependencies and execute callbacks.

    * `service_source(manager, servicename, dirname):`
      Executed when a source tarball service dependency is enumerated.
    """
    deps = b.get('services', {}).get(manager, {}).get(servicename, {})
    if 'sources' not in deps:
        return
    callable = kwargs.get('service_source', lambda *args: None)
    for dirname in list(deps['sources']):
        callable(manager, servicename, dirname)

########NEW FILE########
__FILENAME__ = pydir
from distutils.sysconfig import get_python_version, get_python_lib
import os.path
import sys
for s in ('dist', 'site'):
    pydir = os.path.join(sys.argv[1],
                         'python%s' % get_python_version(),
                         '%s-packages' % s)
    if pydir in sys.path:
        print(pydir)
        sys.exit(0)
print(get_python_lib())

########NEW FILE########
__FILENAME__ = tests
from flask.testing import FlaskClient
import json
import os.path
import sys

from blueprint.io.server import app

SECRET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-'
NAME = 'test'
SHA = 'adff242fbc01ba3753abf8c3f9b45eeedec23ec6'

filename = '{0}.tar'.format(SHA)
pathname = os.path.join(os.path.dirname(__file__), 'tests', filename)

c = app.test_client()

def test_GET_secret():
    response = c.get('/secret')
    assert 201 == response.status_code
    assert 64 + 1 == len(response.data)

def test_PUT_blueprint_invalid_secret():
    response = c.put('/{0}/{1}'.format('invalid', NAME),
                     content_type='application/json',
                     data=json.dumps({}))
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_name():
    response = c.put('/{0}/{1}'.format(SECRET, '%20'),
                     content_type='application/json',
                     data=json.dumps({}))
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_syntax_data():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data='}{')
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_schema_data():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({'invalid': 'invalid'}))
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_length_data():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({
                         'files': {
                             '/etc/long': '.' * 65 * 1024 * 1024,
                         },
                     }))
    assert 413 == response.status_code

def test_PUT_blueprint_empty():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({}))
    assert 202 == response.status_code

def test_PUT_tarball_empty():
    test_PUT_blueprint_empty()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, SHA),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 400 == response.status_code

def test_PUT_blueprint_sources():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({
                         'sources': {
                             '/usr/local': filename,
                         },
                     }))
    assert 202 == response.status_code

def test_PUT_tarball_invalid_sha():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, 'invalid'),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 400 == response.status_code

def test_PUT_tarball_invalid_data():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, '0' * 40),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 400 == response.status_code

def test_PUT_tarball_invalid_length_data():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, '0' * 40),
                     content_type='application/x-tar',
                     data='.' * 65 * 1024 * 1024)
    assert 413 == response.status_code

def test_PUT_tarball():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, SHA),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 202 == response.status_code

def test_GET_blueprint_invalid():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}'.format(SECRET, 'four-oh-four'))
    assert 404 == response.status_code

def test_GET_blueprint():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}'.format(SECRET, NAME))
    assert 301 == response.status_code

def test_GET_blueprint_sh_invalid():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{1}.sh'.format(SECRET, 'four-oh-four'))
    assert 404 == response.status_code

def test_GET_blueprint_sh_mismatch():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{2}.sh'.format(SECRET, 'four-oh-four', 'wrong'))
    assert 400 == response.status_code

def test_GET_blueprint_sh():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{1}.sh'.format(SECRET, NAME))
    assert 200 == response.status_code
    assert '#!' == response.data[0:2]

def test_GET_blueprint_userdata_invalid():
    response = c.get('/{0}/{1}/user-data.sh'.format(SECRET, 'four-oh-four'))
    assert 404 == response.status_code

def test_GET_blueprint_userdata():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/user-data.sh'.format(SECRET, NAME))
    assert 200 == response.status_code
    assert '#!' == response.data[0:2]

def test_GET_tarball_invalid():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{2}.tar'.format(SECRET, NAME, '0' * 40))
    assert 404 == response.status_code

def test_GET_tarball():
    test_PUT_tarball()
    response = c.get('/{0}/{1}/{2}.tar'.format(SECRET, NAME, SHA))
    assert 301 == response.status_code

########NEW FILE########
