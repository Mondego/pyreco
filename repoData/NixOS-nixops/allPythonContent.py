__FILENAME__ = coverage-tests
import nose
import sys
import os

if __name__ == "__main__":
    nose.main(argv=[sys.argv[0], "--with-coverage",
                    "--cover-inclusive", "--cover-xml",
                    "--cover-xml-file=coverage.xml", "--cover-html",
                    "--cover-html-dir=./html", "--cover-package=nixops","--nocapture",
                    "-e", "^tests\.py$"] + sys.argv[1:])

########NEW FILE########
__FILENAME__ = ec2
# -*- coding: utf-8 -*-

import os
import os.path
import sys
import re
import time
import socket
import getpass
import shutil
import boto.ec2
import boto.ec2.blockdevicemapping
from nixops.backends import MachineDefinition, MachineState
from nixops.nix_expr import Function, RawValue
from nixops.resources.ebs_volume import EBSVolumeState
from nixops.resources.elastic_ip import ElasticIPState
import nixops.util
import nixops.ec2_utils
import nixops.known_hosts
from xml import etree

class EC2InstanceDisappeared(Exception):
    pass

class EC2Definition(MachineDefinition):
    """Definition of an EC2 machine."""

    @classmethod
    def get_type(cls):
        return "ec2"

    def __init__(self, xml):
        MachineDefinition.__init__(self, xml)
        x = xml.find("attrs/attr[@name='ec2']/attrs")
        assert x is not None
        self.access_key_id = x.find("attr[@name='accessKeyId']/string").get("value")
        self.type = x.find("attr[@name='type']/string").get("value")
        self.region = x.find("attr[@name='region']/string").get("value")
        self.zone = x.find("attr[@name='zone']/string").get("value")
        self.controller = x.find("attr[@name='controller']/string").get("value")
        self.ami = x.find("attr[@name='ami']/string").get("value")
        if self.ami == "":
            raise Exception("no AMI defined for EC2 machine ‘{0}’".format(self.name))
        self.instance_type = x.find("attr[@name='instanceType']/string").get("value")
        self.key_pair = x.find("attr[@name='keyPair']/string").get("value")
        self.private_key = x.find("attr[@name='privateKey']/string").get("value")
        self.security_groups = [e.get("value") for e in x.findall("attr[@name='securityGroups']/list/string")]
        self.instance_profile = x.find("attr[@name='instanceProfile']/string").get("value")
        self.tags = {k.get("name"): k.find("string").get("value") for k in x.findall("attr[@name='tags']/attrs/attr")}
        self.root_disk_size = int(x.find("attr[@name='ebsInitialRootDiskSize']/int").get("value"))
        self.spot_instance_price = int(x.find("attr[@name='spotInstancePrice']/int").get("value"))
        self.ebs_optimized = x.find("attr[@name='ebsOptimized']/bool").get("value") == "true"

        def f(xml):
            return {'disk': xml.find("attrs/attr[@name='disk']/string").get("value"),
                    'size': int(xml.find("attrs/attr[@name='size']/int").get("value")),
                    'iops': int(xml.find("attrs/attr[@name='iops']/int").get("value")),
                    'fsType': xml.find("attrs/attr[@name='fsType']/string").get("value"),
                    'deleteOnTermination': xml.find("attrs/attr[@name='deleteOnTermination']/bool").get("value") == "true",
                    'encrypt': xml.find("attrs/attr[@name='encrypt']/bool").get("value") == "true",
                    'passphrase': xml.find("attrs/attr[@name='passphrase']/string").get("value")}

        self.block_device_mapping = {_xvd_to_sd(k.get("name")): f(k) for k in x.findall("attr[@name='blockDeviceMapping']/attrs/attr")}
        self.elastic_ipv4 = x.find("attr[@name='elasticIPv4']/string").get("value")

        x = xml.find("attrs/attr[@name='route53']/attrs")
        assert x is not None
        self.dns_hostname = x.find("attr[@name='hostName']/string").get("value")
        self.dns_ttl = x.find("attr[@name='ttl']/int").get("value")
        self.route53_access_key_id = x.find("attr[@name='accessKeyId']/string").get("value")

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region or self.zone or "???")


class EC2State(MachineState):
    """State of an EC2 machine."""

    @classmethod
    def get_type(cls):
        return "ec2"

    state = nixops.util.attr_property("state", MachineState.MISSING, int)  # override
    public_ipv4 = nixops.util.attr_property("publicIpv4", None)
    private_ipv4 = nixops.util.attr_property("privateIpv4", None)
    elastic_ipv4 = nixops.util.attr_property("ec2.elasticIpv4", None)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    region = nixops.util.attr_property("ec2.region", None)
    zone = nixops.util.attr_property("ec2.zone", None)
    controller = nixops.util.attr_property("ec2.controller", None)  # FIXME: not used
    ami = nixops.util.attr_property("ec2.ami", None)
    instance_type = nixops.util.attr_property("ec2.instanceType", None)
    key_pair = nixops.util.attr_property("ec2.keyPair", None)
    public_host_key = nixops.util.attr_property("ec2.publicHostKey", None)
    private_host_key = nixops.util.attr_property("ec2.privateHostKey", None)
    private_key_file = nixops.util.attr_property("ec2.privateKeyFile", None)
    instance_profile = nixops.util.attr_property("ec2.instanceProfile", None)
    security_groups = nixops.util.attr_property("ec2.securityGroups", None, 'json')
    tags = nixops.util.attr_property("ec2.tags", {}, 'json')
    block_device_mapping = nixops.util.attr_property("ec2.blockDeviceMapping", {}, 'json')
    root_device_type = nixops.util.attr_property("ec2.rootDeviceType", None)
    backups = nixops.util.attr_property("ec2.backups", {}, 'json')
    dns_hostname = nixops.util.attr_property("route53.hostName", None)
    dns_ttl = nixops.util.attr_property("route53.ttl", None, int)
    route53_access_key_id = nixops.util.attr_property("route53.accessKeyId", None)
    client_token = nixops.util.attr_property("ec2.clientToken", None)
    spot_instance_request_id = nixops.util.attr_property("ec2.spotInstanceRequestId", None)
    spot_instance_price = nixops.util.attr_property("ec2.spotInstancePrice", None)

    def __init__(self, depl, name, id):
        MachineState.__init__(self, depl, name, id)
        self._conn = None
        self._conn_route53 = None


    def _reset_state(self):
        """Discard all state pertaining to an instance."""
        with self.depl._db:
            self.state = MachineState.MISSING
            self.vm_id = None
            self.public_ipv4 = None
            self.private_ipv4 = None
            self.elastic_ipv4 = None
            self.region = None
            self.zone = None
            self.controller = None
            self.ami = None
            self.instance_type = None
            self.key_pair = None
            self.public_host_key = None
            self.private_host_key = None
            self.instance_profile = None
            self.security_groups = None
            self.tags = {}
            self.block_device_mapping = {}
            self.root_device_type = None
            self.backups = {}
            self.dns_hostname = None
            self.dns_ttl = None


    def get_ssh_name(self):
        if not self.public_ipv4:
            raise Exception("EC2 machine ‘{0}’ does not have a public IPv4 address (yet)".format(self.name))
        return self.public_ipv4


    def get_ssh_private_key_file(self):
        if self.private_key_file: return self.private_key_file
        if self._ssh_private_key_file: return self._ssh_private_key_file
        for r in self.depl.active_resources.itervalues():
            if isinstance(r, nixops.resources.ec2_keypair.EC2KeyPairState) and \
                    r.state == nixops.resources.ec2_keypair.EC2KeyPairState.UP and \
                    r.keypair_name == self.key_pair:
                return self.write_ssh_private_key(r.private_key)
        return None


    def get_ssh_flags(self):
        file = self.get_ssh_private_key_file()
        return ["-i", file] if file else []


    def get_physical_spec(self):
        block_device_mapping = {}
        for k, v in self.block_device_mapping.items():
            if (v.get('encrypt', False)
                and v.get('passphrase', "") == ""
                and v.get('generatedKey', "") != ""):
                block_device_mapping[_sd_to_xvd(k)] = {
                    'passphrase': Function("pkgs.lib.mkOverride 10",
                                           v['generatedKey'], call=True),
                }

        return {
            'require': [
                RawValue("<nixpkgs/nixos/modules/virtualisation/amazon-config.nix>")
            ],
            ('deployment', 'ec2', 'blockDeviceMapping'): block_device_mapping,
            ('deployment', 'ec2', 'instanceId'): self.vm_id,
        }

    def get_physical_backup_spec(self, backupid):
        val = {}
        if backupid in self.backups:
            for dev, snap in self.backups[backupid].items():
                if not dev.startswith("/dev/sda"):
                    val[_sd_to_xvd(dev)] = { 'disk': Function("pkgs.lib.mkOverride 10", snap, call=True)}
            val = { ('deployment', 'ec2', 'blockDeviceMapping'): val }
        else:
            val = RawValue("{{}} /* No backup found for id '{0}' */".format(backupid))
        return Function("{ config, pkgs, ... }", val)


    def get_keys(self):
        keys = MachineState.get_keys(self)
        # Ugly: we have to add the generated keys because they're not
        # there in the first evaluation (though they are present in
        # the final nix-build).
        for k, v in self.block_device_mapping.items():
            if v.get('encrypt', False) and v.get('passphrase', "") == "" and v.get('generatedKey', "") != "":
                keys["luks-" + _sd_to_xvd(k).replace('/dev/', '')] = v['generatedKey']
        return keys


    def show_type(self):
        s = super(EC2State, self).show_type()
        if self.zone or self.region: s = "{0} [{1}; {2}]".format(s, self.zone or self.region, self.instance_type)
        return s


    @property
    def resource_id(self):
        return self.vm_id


    def address_to(self, m):
        if isinstance(m, EC2State): # FIXME: only if we're in the same region
            return m.private_ipv4
        return MachineState.address_to(self, m)


    def disk_volume_options(self, v):
        if v['iops'] != 0 and not v['iops'] is None:
            iops = v['iops']
            volume_type = 'io1'
        else:
            iops = None
            volume_type = 'standard'
        return (volume_type, iops)


    def connect(self):
        if self._conn: return self._conn
        self._conn = nixops.ec2_utils.connect(self.region, self.access_key_id)
        return self._conn


    def connect_route53(self):
        if self._conn_route53:
            return

        # Get the secret access key from the environment or from ~/.ec2-keys.
        (access_key_id, secret_access_key) = nixops.ec2_utils.fetch_aws_secret_key(self.route53_access_key_id)

        self._conn_route53 = boto.connect_route53(access_key_id, secret_access_key)

    def _get_spot_instance_request_by_id(self, request_id, allow_missing=False):
        """Get spot instance request object by id."""
        self.connect()
        result = self._conn.get_all_spot_instance_requests([request_id])
        if len(result) == 0:
            if allow_missing:
                return None
            raise EC2InstanceDisappeared("Spot instance request ‘{0}’ disappeared!".format(request_id))
        return result[0]


    def _get_instance_by_id(self, instance_id, allow_missing=False):
        """Get instance object by instance id."""
        self.connect()
        reservations = self._conn.get_all_instances([instance_id])
        if len(reservations) == 0:
            if allow_missing:
                return None
            raise EC2InstanceDisappeared("EC2 instance ‘{0}’ disappeared!".format(instance_id))
        return reservations[0].instances[0]


    def _get_snapshot_by_id(self, snapshot_id):
        """Get snapshot object by instance id."""
        self.connect()
        snapshots = self._conn.get_all_snapshots([snapshot_id])
        if len(snapshots) != 1:
            raise Exception("unable to find snapshot ‘{0}’".format(snapshot_id))
        return snapshots[0]


    def _wait_for_ip(self, instance):
        self.log_start("waiting for IP address... ".format(self.name))

        while True:
            instance.update()
            self.log_continue("[{0}] ".format(instance.state))
            if instance.state not in {"pending", "running", "scheduling", "launching", "stopped"}:
                raise Exception("EC2 instance ‘{0}’ failed to start (state is ‘{1}’)".format(self.vm_id, instance.state))
            if instance.state != "running":
                time.sleep(3)
                continue
            if instance.ip_address:
                break
            time.sleep(3)

        self.log_end("{0} / {1}".format(instance.ip_address, instance.private_ip_address))

        nixops.known_hosts.add(instance.ip_address, self.public_host_key)

        self.private_ipv4 = instance.private_ip_address
        self.public_ipv4 = instance.ip_address
        self.ssh_pinged = False


    def _booted_from_ebs(self):
        return self.root_device_type == "ebs"

    def update_block_device_mapping(self, k, v):
        x = self.block_device_mapping
        if v == None:
            x.pop(k, None)
        else:
            x[k] = v
        self.block_device_mapping = x


    def get_backups(self):
        self.connect()
        backups = {}
        current_volumes = set([v['volumeId'] for v in self.block_device_mapping.values()])
        for b_id, b in self.backups.items():
            backups[b_id] = {}
            backup_status = "complete"
            info = []
            for k, v in self.block_device_mapping.items():
                if not k in b.keys():
                    backup_status = "incomplete"
                    info.append("{0} - {1} - Not available in backup".format(self.name, _sd_to_xvd(k)))
                else:
                    snapshot_id = b[k]
                    try:
                        snapshot = self._get_snapshot_by_id(snapshot_id)
                        snapshot_status = snapshot.update()
                        info.append("progress[{0},{1},{2}] = {3}".format(self.name, _sd_to_xvd(k), snapshot_id, snapshot_status))
                        if snapshot_status != '100%':
                            backup_status = "running"
                    except boto.exception.EC2ResponseError as e:
                        if e.error_code != "InvalidSnapshot.NotFound": raise
                        info.append("{0} - {1} - {2} - Snapshot has disappeared".format(self.name, _sd_to_xvd(k), snapshot_id))
                        backup_status = "unavailable"
            backups[b_id]['status'] = backup_status
            backups[b_id]['info'] = info
        return backups


    def remove_backup(self, backup_id):
        self.log('removing backup {0}'.format(backup_id))
        self.connect()
        _backups = self.backups
        if not backup_id in _backups.keys():
            self.warn('backup {0} not found, skipping'.format(backup_id))
        else:
            for dev, snapshot_id in _backups[backup_id].items():
                snapshot = None
                try:
                    snapshot = self._get_snapshot_by_id(snapshot_id)
                except:
                    self.warn('snapshot {0} not found, skipping'.format(snapshot_id))
                if not snapshot is None:
                    self.log('removing snapshot {0}'.format(snapshot_id))
                    nixops.ec2_utils.retry(lambda: snapshot.delete())

            _backups.pop(backup_id)
            self.backups = _backups


    def get_common_tags(self):
        return {'CharonNetworkUUID': self.depl.uuid,
                'CharonMachineName': self.name,
                'CharonStateFile': "{0}@{1}:{2}".format(getpass.getuser(), socket.gethostname(), self.depl._db.db_file)}

    def backup(self, defn, backup_id):
        self.connect()

        self.log("backing up machine ‘{0}’ using id ‘{1}’".format(self.name, backup_id))
        backup = {}
        _backups = self.backups
        for k, v in self.block_device_mapping.items():
            snapshot = nixops.ec2_utils.retry(lambda: self._conn.create_snapshot(volume_id=v['volumeId']))
            self.log("+ created snapshot of volume ‘{0}’: ‘{1}’".format(v['volumeId'], snapshot.id))

            snapshot_tags = {}
            snapshot_tags.update(defn.tags)
            snapshot_tags.update(self.get_common_tags())
            snapshot_tags['Name'] = "{0} - {3} [{1} - {2}]".format(self.depl.description, self.name, k, backup_id)

            nixops.ec2_utils.retry(lambda: self._conn.create_tags([snapshot.id], snapshot_tags))
            backup[k] = snapshot.id
        _backups[backup_id] = backup
        self.backups = _backups


    def restore(self, defn, backup_id, devices=[]):
        self.stop()

        self.log("restoring machine ‘{0}’ to backup ‘{1}’".format(self.name, backup_id))
        for d in devices:
            self.log(" - {0}".format(d))

        for k, v in self.block_device_mapping.items():
            if devices == [] or _sd_to_xvd(k) in devices:
                # detach disks
                volume = nixops.ec2_utils.get_volume_by_id(self.connect(), v['volumeId'])
                if volume and volume.update() == "in-use":
                    self.log("detaching volume from ‘{0}’".format(self.name))
                    volume.detach()

                # attach backup disks
                snapshot_id = self.backups[backup_id][k]
                self.log("creating volume from snapshot ‘{0}’".format(snapshot_id))
                new_volume = self._conn.create_volume(size=0, snapshot=snapshot_id, zone=self.zone)

                # check if original volume is available, aka detached from the machine
                self.wait_for_volume_available(volume)
                # check if new volume is available
                self.wait_for_volume_available(new_volume)

                self.log("attaching volume ‘{0}’ to ‘{1}’".format(new_volume.id, self.name))
                new_volume.attach(self.vm_id, k)
                new_v = self.block_device_mapping[k]
                if v.get('partOfImage', False) or v.get('charonDeleteOnTermination', False) or v.get('deleteOnTermination', False):
                    new_v['charonDeleteOnTermination'] = True
                    self._delete_volume(v['volumeId'], True)
                new_v['volumeId'] = new_volume.id
                self.update_block_device_mapping(k, new_v)


    def create_after(self, resources):
        # EC2 instances can require key pairs, IAM roles, security
        # groups, EBS volumes and elastic IPs.  FIXME: only depend on
        # the specific key pair / role needed for this instance.
        return {r for r in resources if
                isinstance(r, nixops.resources.ec2_keypair.EC2KeyPairState) or
                isinstance(r, nixops.resources.iam_role.IAMRoleState) or
                isinstance(r, nixops.resources.ec2_security_group.EC2SecurityGroupState) or
                isinstance(r, nixops.resources.ebs_volume.EBSVolumeState) or
                isinstance(r, nixops.resources.elastic_ip.ElasticIPState)}


    def attach_volume(self, device, volume_id):
        volume = nixops.ec2_utils.get_volume_by_id(self.connect(), volume_id)
        if volume.status == "in-use" and \
            self.vm_id != volume.attach_data.instance_id and \
            self.depl.logger.confirm("volume ‘{0}’ is in use by instance ‘{1}’, "
                                     "are you sure you want to attach this volume?".format(volume_id, volume.attach_data.instance_id)):

            self.log_start("detaching volume ‘{0}’ from instance ‘{1}’...".format(volume_id, volume.attach_data.instance_id))
            volume.detach()

            def check_available():
                res = volume.update()
                self.log_continue("[{0}] ".format(res))
                return res == 'available'

            nixops.util.check_wait(check_available)
            self.log_end('')

            if volume.update() != "available":
                self.log("force detaching volume ‘{0}’ from instance ‘{1}’...".format(volume_id, volume.attach_data.instance_id))
                volume.detach(True)
                nixops.util.check_wait(check_available)

        self.log_start("attaching volume ‘{0}’ as ‘{1}’...".format(volume_id, _sd_to_xvd(device)))
        if self.vm_id != volume.attach_data.instance_id:
            # Attach it.
            self._conn.attach_volume(volume_id, self.vm_id, device)

        def check_attached():
            volume.update()
            res = volume.attach_data.status
            self.log_continue("[{0}] ".format(res))
            return res == 'attached'

        # If volume is not in attached state, wait for it before going on.
        if volume.attach_data.status != "attached":
            nixops.util.check_wait(check_attached)

        # Wait until the device is visible in the instance.
        def check_dev():
            res = self.run_command("test -e {0}".format(_sd_to_xvd(device)), check=False)
            return res == 0
        nixops.util.check_wait(check_dev)

        self.log_end('')


    def wait_for_volume_available(self, volume):
        def check_available():
            res = volume.update()
            self.log_continue("[{0}] ".format(res))
            return res == 'available'

        nixops.util.check_wait(check_available, max_tries=90)
        self.log_end('')


    def assign_elastic_ip(self, elastic_ipv4, instance, check):
        # Assign or release an elastic IP address, if given.
        if (self.elastic_ipv4 or "") != elastic_ipv4 or (instance.ip_address != elastic_ipv4) or check:
            if elastic_ipv4 != "":
                # wait until machine is in running state
                self.log_start("waiting for machine to be in running state... ".format(self.name))
                while True:
                    self.log_continue("[{0}] ".format(instance.state))
                    if instance.state == "running":
                        break
                    if instance.state not in {"running", "pending"}:
                        raise Exception(
                            "EC2 instance ‘{0}’ failed to reach running state (state is ‘{1}’)"
                            .format(self.vm_id, instance.state))
                    time.sleep(3)
                    instance.update()
                self.log_end("")

                addresses = self._conn.get_all_addresses(addresses=[elastic_ipv4])
                if addresses[0].instance_id != "" \
                    and addresses[0].instance_id != self.vm_id \
                    and not self.depl.logger.confirm(
                        "are you sure you want to associate IP address ‘{0}’, which is currently in use by instance ‘{1}’?".format(
                            elastic_ipv4, addresses[0].instance_id)):
                    raise Exception("elastic IP ‘{0}’ already in use...".format(elastic_ipv4))
                else:
                    self.log("associating IP address ‘{0}’...".format(elastic_ipv4))
                    addresses[0].associate(self.vm_id)
                    self.log_start("waiting for address to be associated with this machine... ")
                    instance.update()
                    while True:
                        self.log_continue("[{0}] ".format(instance.ip_address))
                        if instance.ip_address == elastic_ipv4:
                            break
                        time.sleep(3)
                        instance.update()
                    self.log_end("")

                nixops.known_hosts.add(elastic_ipv4, self.public_host_key)
                with self.depl._db:
                    self.elastic_ipv4 = elastic_ipv4
                    self.public_ipv4 = elastic_ipv4
                    self.ssh_pinged = False

            elif self.elastic_ipv4 != None:
                self.log("disassociating IP address ‘{0}’...".format(self.elastic_ipv4))
                self._conn.disassociate_address(public_ip=self.elastic_ipv4)
                with self.depl._db:
                    self.elastic_ipv4 = None
                    self.public_ipv4 = None
                    self.ssh_pinged = False



    def create_instance(self, defn, zone, devmap, user_data, ebs_optimized):
        common_args = dict(
            instance_type=defn.instance_type,
            placement=zone,
            key_name=defn.key_pair,
            security_groups=defn.security_groups,
            block_device_map=devmap,
            user_data=user_data,
            image_id=defn.ami,
            ebs_optimized=ebs_optimized
        )
        if defn.instance_profile.startswith("arn:") :
            common_args['instance_profile_arn'] = defn.instance_profile
        else:
            common_args['instance_profile_name'] = defn.instance_profile

        if defn.spot_instance_price:
            request = nixops.ec2_utils.retry(
                lambda: self._conn.request_spot_instances(price=defn.spot_instance_price/100.0, **common_args)
            )[0]

            common_tags = self.get_common_tags()
            tags = {'Name': "{0} [{1}]".format(self.depl.description, self.name)}
            tags.update(defn.tags)
            tags.update(common_tags)
            nixops.ec2_utils.retry(lambda: self._conn.create_tags([request.id], tags))

            self.spot_instance_price = defn.spot_instance_price
            self.spot_instance_request_id = request.id

            self.log_start("Waiting for spot instance request to be fulfilled. ")
            def check_request():
                req = self._get_spot_instance_request_by_id(request.id)
                self.log_continue("[{0}] ".format(req.status.code))
                return req.status.code == "fulfilled"
            self.log_end("")

            try:
                nixops.util.check_wait(test=check_request)
            finally:
                # cancel spot instance request, it isn't needed after instance is provisioned
                self.spot_instance_request_id = None
                self._conn.cancel_spot_instance_requests([request.id])

            request = self._get_spot_instance_request_by_id(request.id)

            instance = nixops.ec2_utils.retry(lambda: self._get_instance_by_id(request.instance_id))

            return instance
        else:
            reservation = nixops.ec2_utils.retry(lambda: self._conn.run_instances(
                client_token=self.client_token, **common_args), error_codes = ['InvalidParameterValue', 'UnauthorizedOperation' ])

            assert len(reservation.instances) == 1
            return reservation.instances[0]

    def after_activation(self, defn):
        # Detach volumes that are no longer in the deployment spec.
        for k, v in self.block_device_mapping.items():
            if k not in defn.block_device_mapping and not v.get('partOfImage', False):
                if v['disk'].startswith("ephemeral"):
                    raise Exception("cannot detach ephemeral device ‘{0}’ from EC2 instance ‘{1}’"
                    .format(_sd_to_xvd(k), self.name))

                assert v.get('volumeId', None)

                self.log("detaching device ‘{0}’...".format(_sd_to_xvd(k)))
                volumes = self._conn.get_all_volumes([],
                    filters={'attachment.instance-id': self.vm_id, 'attachment.device': k, 'volume-id': v['volumeId']})
                assert len(volumes) <= 1

                if len(volumes) == 1:
                    device = _sd_to_xvd(k)
                    if v.get('encrypt', False):
                        dm = device.replace("/dev/", "/dev/mapper/")
                        self.run_command("umount -l {0}".format(dm), check=False)
                        self.run_command("cryptsetup luksClose {0}".format(device.replace("/dev/", "")), check=False)
                    else:
                        self.run_command("umount -l {0}".format(device), check=False)
                    if not self._conn.detach_volume(volumes[0].id, instance_id=self.vm_id, device=k):
                        raise Exception("unable to detach device ‘{0}’ from EC2 machine ‘{1}’".format(v['disk'], self.name))
                        # FIXME: Wait until the volume is actually detached.

                if v.get('charonDeleteOnTermination', False) or v.get('deleteOnTermination', False):
                    self._delete_volume(v['volumeId'])

                self.update_block_device_mapping(k, None)


    def create(self, defn, check, allow_reboot, allow_recreate):
        assert isinstance(defn, EC2Definition)
        assert defn.type == "ec2"

        if self.state != self.UP:
            check = True

        self.set_common_state(defn)

        # Figure out the access key.
        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘deployment.ec2.accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        self.private_key_file = defn.private_key or None
        self.owners = defn.owners

        # Stop the instance (if allowed) to change instance attributes
        # such as the type.
        if self.vm_id and allow_reboot and self._booted_from_ebs() and self.instance_type != defn.instance_type:
            self.stop()
            check = True

        # Check whether the instance hasn't been killed behind our
        # backs.  Restart stopped instances.
        if self.vm_id and check:
            self.connect()
            instance = self._get_instance_by_id(self.vm_id, allow_missing=True)
            if instance is None or instance.state in {"shutting-down", "terminated"}:
                if not allow_recreate:
                    raise Exception("EC2 instance ‘{0}’ went away; use ‘--allow-recreate’ to create a new one".format(self.name))
                self.log("EC2 instance went away (state ‘{0}’), will recreate".format(instance.state if instance else "gone"))
                self._reset_state()
            elif instance.state == "stopped":
                self.log("EC2 instance was stopped, restarting...")

                # Modify the instance type, if desired.
                if self.instance_type != defn.instance_type:
                    self.log("changing instance type from ‘{0}’ to ‘{1}’...".format(self.instance_type, defn.instance_type))
                    instance.modify_attribute("instanceType", defn.instance_type)
                    self.instance_type = defn.instance_type

                # When we restart, we'll probably get a new IP.  So forget the current one.
                self.public_ipv4 = None
                self.private_ipv4 = None

                instance.start()

                self.state = self.STARTING

        resize_root = False

        # Create the instance.
        if not self.vm_id:
            self.log("creating EC2 instance (AMI ‘{0}’, type ‘{1}’, region ‘{2}’)...".format(
                defn.ami, defn.instance_type, defn.region))
            if not self.client_token: self._reset_state()

            self.region = defn.region
            self.connect()

            # Figure out whether this AMI is EBS-backed.
            ami = self._conn.get_all_images([defn.ami])[0]
            self.root_device_type = ami.root_device_type

            # Check if we need to resize the root disk
            resize_root = defn.root_disk_size != 0 and ami.root_device_type == 'ebs'

            # Set the initial block device mapping to the ephemeral
            # devices defined in the spec.  These cannot be changed
            # later.
            devmap = boto.ec2.blockdevicemapping.BlockDeviceMapping()
            devs_mapped = {}
            for k, v in defn.block_device_mapping.iteritems():
                if re.match("/dev/sd[a-e]", k) and not v['disk'].startswith("ephemeral"):
                    raise Exception("non-ephemeral disk not allowed on device ‘{0}’; use /dev/xvdf or higher".format(_sd_to_xvd(k)))
                if v['disk'].startswith("ephemeral"):
                    devmap[k] = boto.ec2.blockdevicemapping.BlockDeviceType(ephemeral_name=v['disk'])
                    self.update_block_device_mapping(k, v)

            root_device = ami.root_device_name
            if resize_root:
                devmap[root_device] = ami.block_device_mapping[root_device]
                devmap[root_device].size = defn.root_disk_size

            # If we're attaching any EBS volumes, then make sure that
            # we create the instance in the right placement zone.
            zone = defn.zone or None
            for k, v in defn.block_device_mapping.iteritems():
                if not v['disk'].startswith("vol-"): continue
                # Make note of the placement zone of the volume.
                volume = nixops.ec2_utils.get_volume_by_id(self.connect(), v['disk'])
                if not zone:
                    self.log("starting EC2 instance in zone ‘{0}’ due to volume ‘{1}’".format(
                            volume.zone, v['disk']))
                    zone = volume.zone
                elif zone != volume.zone:
                    raise Exception("unable to start EC2 instance ‘{0}’ in zone ‘{1}’ because volume ‘{2}’ is in zone ‘{3}’"
                                    .format(self.name, zone, v['disk'], volume.zone))

            # Do we want an EBS-optimized instance?
            prefer_ebs_optimized = False
            for k, v in defn.block_device_mapping.iteritems():
                (volume_type, iops) = self.disk_volume_options(v)
                if volume_type != "standard": prefer_ebs_optimized = True

            # if we have PIOPS volume and instance type supports EBS Optimized flags, then use ebs_optimized
            ebs_optimized = prefer_ebs_optimized and defn.ebs_optimized

            # Generate a public/private host key.
            if not self.public_host_key:
                (private, public) = nixops.util.create_key_pair(type='dsa')
                with self.depl._db:
                    self.public_host_key = public
                    self.private_host_key = private

            user_data = "SSH_HOST_DSA_KEY_PUB:{0}\nSSH_HOST_DSA_KEY:{1}\n".format(
                self.public_host_key, self.private_host_key.replace("\n", "|"))

            # Use a client token to ensure that instance creation is
            # idempotent; i.e., if we get interrupted before recording
            # the instance ID, we'll get the same instance ID on the
            # next run.
            if not self.client_token:
                with self.depl._db:
                    self.client_token = nixops.util.generate_random_string(length=48) # = 64 ASCII chars
                    self.state = self.STARTING

            instance = self.create_instance(defn, zone, devmap, user_data, ebs_optimized)

            with self.depl._db:
                self.vm_id = instance.id
                self.controller = defn.controller
                self.ami = defn.ami
                self.instance_type = defn.instance_type
                self.key_pair = defn.key_pair
                self.security_groups = defn.security_groups
                self.zone = instance.placement
                self.client_token = None
                self.private_host_key = None

        # There is a short time window during which EC2 doesn't
        # know the instance ID yet.  So wait until it does.
        while True:
            try:
                instance = self._get_instance_by_id(self.vm_id)
                break
            except EC2InstanceDisappeared:
                pass
            except boto.exception.EC2ResponseError as e:
                if e.error_code != "InvalidInstanceID.NotFound":
                    raise
            self.log("EC2 instance ‘{0}’ not known yet, waiting...".format(self.vm_id))
            time.sleep(3)

        # Warn about some EC2 options that we cannot update for an existing instance.
        if self.instance_type != defn.instance_type:
            self.warn("cannot change type of a running instance (use ‘--allow-reboot’)")
        if self.region != defn.region:
            self.warn("cannot change region of a running instance")
        if defn.zone and self.zone != defn.zone:
            self.warn("cannot change availability zone of a running instance")
        instance_groups = set([g.name for g in instance.groups])
        if set(defn.security_groups) != instance_groups:
            self.warn(
                'cannot change security groups of an existing instance (from [{0}] to [{1}])'.format(
                    ", ".join(set(defn.security_groups)),
                    ", ".join(instance_groups))
            )

        # Reapply tags if they have changed.
        common_tags = self.get_common_tags()

        if self.owners != []:
            common_tags['Owners'] = ", ".join(self.owners)

        tags = {'Name': "{0} [{1}]".format(self.depl.description, self.name)}
        tags.update(defn.tags)
        tags.update(common_tags)
        if check or self.tags != tags:
            nixops.ec2_utils.retry(lambda: self._conn.create_tags([self.vm_id], tags))
            # TODO: remove obsolete tags?
            self.tags = tags

        # Assign the elastic IP.  If necessary, dereference the resource.
        elastic_ipv4 = defn.elastic_ipv4
        if elastic_ipv4.startswith("res-"):
            res = self.depl.get_typed_resource(elastic_ipv4[4:], "elastic-ip")
            elastic_ipv4 = res.public_ipv4
        self.assign_elastic_ip(elastic_ipv4, instance, check)

        # Wait for the IP address.
        if not self.public_ipv4 or check:
            instance = self._get_instance_by_id(self.vm_id)
            self._wait_for_ip(instance)

        if defn.dns_hostname:
            self._update_route53(defn)

        # Wait until the instance is reachable via SSH.
        self.wait_for_ssh(check=check)

        if resize_root:
            self.log('resizing root disk...')
            self.run_command("resize2fs {0}".format(_sd_to_xvd(root_device)))

        # Add disks that were in the original device mapping of image.
        for k, dm in instance.block_device_mapping.items():
            if k not in self.block_device_mapping and dm.volume_id:
                bdm = {'volumeId': dm.volume_id, 'partOfImage': True}
                self.update_block_device_mapping(k, bdm)

        # Detect if volumes were manually detached.  If so, reattach
        # them.
        for k, v in self.block_device_mapping.items():
            if k not in instance.block_device_mapping.keys() and not v.get('needsAttach', False) and v.get('volumeId', None):
                self.warn("device ‘{0}’ was manually detached!".format(_sd_to_xvd(k)))
                v['needsAttach'] = True
                self.update_block_device_mapping(k, v)

        # Detect if volumes were manually destroyed.
        for k, v in self.block_device_mapping.items():
            if v.get('needsAttach', False):
                print v['volumeId']
                volume = nixops.ec2_utils.get_volume_by_id(self.connect(), v['volumeId'], allow_missing=True)
                if volume: continue
                if not allow_recreate:
                    raise Exception("volume ‘{0}’ (used by EC2 instance ‘{1}’) no longer exists; "
                                    "run ‘nixops stop’, then ‘nixops deploy --allow-recreate’ to create a new, empty volume"
                                    .format(v['volumeId'], self.name))
                self.warn("volume ‘{0}’ has disappeared; will create an empty volume to replace it".format(v['volumeId']))
                self.update_block_device_mapping(k, None)

        # Create missing volumes.
        for k, v in defn.block_device_mapping.iteritems():

            volume = None
            if v['disk'] == '':
                if k in self.block_device_mapping: continue
                self.log("creating EBS volume of {0} GiB...".format(v['size']))
                (volume_type, iops) = self.disk_volume_options(v)
                volume = self._conn.create_volume(size=v['size'], zone=self.zone, volume_type=volume_type, iops=iops)
                v['volumeId'] = volume.id

            elif v['disk'].startswith("vol-"):
                if k in self.block_device_mapping:
                    cur_volume_id = self.block_device_mapping[k]['volumeId']
                    if cur_volume_id != v['disk']:
                        raise Exception("cannot attach EBS volume ‘{0}’ to ‘{1}’ because volume ‘{2}’ is already attached there".format(v['disk'], k, cur_volume_id))
                    continue
                v['volumeId'] = v['disk']

            elif v['disk'].startswith("res-"):
                res_name = v['disk'][4:]
                res = self.depl.get_typed_resource(res_name, "ebs-volume")
                if res.state != self.UP:
                    raise Exception("EBS volume ‘{0}’ has not been created yet".format(res_name))
                assert res.volume_id
                if k in self.block_device_mapping:
                    cur_volume_id = self.block_device_mapping[k]['volumeId']
                    if cur_volume_id != res.volume_id:
                        raise Exception("cannot attach EBS volume ‘{0}’ to ‘{1}’ because volume ‘{2}’ is already attached there".format(res_name, k, cur_volume_id))
                    continue
                v['volumeId'] = res.volume_id

            elif v['disk'].startswith("snap-"):
                if k in self.block_device_mapping: continue
                self.log("creating volume from snapshot ‘{0}’...".format(v['disk']))
                (volume_type, iops) = self.disk_volume_options(v)
                volume = self._conn.create_volume(size=0, snapshot=v['disk'], zone=self.zone, volume_type=volume_type, iops=iops)
                v['volumeId'] = volume.id

            else:
                raise Exception("adding device mapping ‘{0}’ to a running instance is not (yet) supported".format(v['disk']))

            # ‘charonDeleteOnTermination’ denotes whether we have to
            # delete the volume.  This is distinct from
            # ‘deleteOnTermination’ for backwards compatibility with
            # the time that we still used auto-created volumes.
            v['charonDeleteOnTermination'] = v['deleteOnTermination']
            v['needsAttach'] = True
            self.update_block_device_mapping(k, v)

            # Wait for volume to get to available state for newly
            # created volumes only (EC2 sometimes returns weird
            # temporary states for newly created volumes, e.g. shortly
            # in-use).  Doing this after updating the device mapping
            # state, to make it recoverable in case an exception
            # happens (e.g. in other machine's deployments).
            if volume: self.wait_for_volume_available(volume)

        # Always apply tags to all volumes
        for k, v in self.block_device_mapping.items():
            # Tag the volume.
            volume_tags = {}
            volume_tags.update(common_tags)
            volume_tags.update(defn.tags)
            volume_tags['Name'] = "{0} [{1} - {2}]".format(self.depl.description, self.name, _sd_to_xvd(k))
            if 'disk' in v and not v['disk'].startswith("ephemeral"):
                nixops.ec2_utils.retry(lambda: self._conn.create_tags([v['volumeId']], volume_tags))

        # Attach missing volumes.
        for k, v in self.block_device_mapping.items():
            if v.get('needsAttach', False):
                self.attach_volume(k, v['volumeId'])
                del v['needsAttach']
                self.update_block_device_mapping(k, v)

        # FIXME: process changes to the deleteOnTermination flag.

        # Auto-generate LUKS keys if the model didn't specify one.
        for k, v in self.block_device_mapping.items():
            if v.get('encrypt', False) and v.get('passphrase', "") == "" and v.get('generatedKey', "") == "":
                v['generatedKey'] = nixops.util.generate_random_string(length=256)
                self.update_block_device_mapping(k, v)


    def _update_route53(self, defn):
        import boto.route53
        import boto.route53.record

        self.dns_hostname = defn.dns_hostname
        self.dns_ttl = defn.dns_ttl
        self.route53_access_key_id = defn.route53_access_key_id

        self.log('sending Route53 DNS: {0} {1}'.format(self.public_ipv4, self.dns_hostname))

        self.connect_route53()

        hosted_zone = ".".join(self.dns_hostname.split(".")[1:])
        zones = self._conn_route53.get_all_hosted_zones()

        def testzone(hosted_zone, zone):
            """returns True if there is a subcomponent match"""
            hostparts = hosted_zone.split(".")
            zoneparts = zone.Name.split(".")[:-1] # strip the last ""

            return hostparts[::-1][:len(zoneparts)][::-1] == zoneparts

        zones = [zone for zone in zones['ListHostedZonesResponse']['HostedZones'] if testzone(hosted_zone, zone)]
        if len(zones) == 0:
            raise Exception('hosted zone for {0} not found'.format(hosted_zone))

        zones = sorted(zones, cmp=lambda a, b: cmp(len(a), len(b)), reverse=True)
        zoneid = zones[0]['Id'].split("/")[2]

        # name argument does not filter, just is a starting point, annoying.. copying into a separate list
        all_prevrrs = self._conn_route53.get_all_rrsets(hosted_zone_id=zoneid, type="A", name="{0}.".format(self.dns_hostname))
        prevrrs = []
        for prevrr in all_prevrrs:
            if prevrr.name == "{0}.".format(self.dns_hostname):
                prevrrs.append(prevrr)

        changes = boto.route53.record.ResourceRecordSets(connection=self._conn_route53, hosted_zone_id=zoneid)
        if len(prevrrs) > 0:
            for prevrr in prevrrs:
                change = changes.add_change("DELETE", self.dns_hostname, "A")
                change.add_value(",".join(prevrr.resource_records))

        change = changes.add_change("CREATE", self.dns_hostname, "A")
        change.add_value(self.public_ipv4)
        self._commit_route53_changes(changes)


    def _commit_route53_changes(self, changes):
        """Commit changes, but retry PriorRequestNotComplete errors."""
        retry = 3
        while True:
            try:
                retry -= 1
                return changes.commit()
            except boto.route53.exception.DNSServerError, e:
                code = e.body.split("<Code>")[1]
                code = code.split("</Code>")[0]
                if code != 'PriorRequestNotComplete' or retry < 0:
                    raise e
                time.sleep(1)


    def _delete_volume(self, volume_id, allow_keep=False):
        if not self.depl.logger.confirm("are you sure you want to destroy EC2 volume ‘{0}’?".format(volume_id)):
            if allow_keep:
                return
            else:
                raise Exception("not destroying EC2 volume ‘{0}’".format(volume_id))
        self.log("destroying EC2 volume ‘{0}’...".format(volume_id))
        volume = nixops.ec2_utils.get_volume_by_id(self.connect(), volume_id, allow_missing=True)
        if not volume: return
        nixops.util.check_wait(lambda: volume.update() == 'available')
        volume.delete()


    def destroy(self, wipe=False):
        if not (self.vm_id or self.client_token): return True
        if not self.depl.logger.confirm("are you sure you want to destroy EC2 machine ‘{0}’?".format(self.name)): return False

        self.log_start("destroying EC2 machine... ".format(self.name))

        # Find the instance, either by its ID or by its client token.
        # The latter allows us to destroy instances that were "leaked"
        # in create() due to it being interrupted after the instance
        # was created but before it registered the ID in the database.
        self.connect()
        instance = None
        if self.vm_id:
            instance = self._get_instance_by_id(self.vm_id, allow_missing=True)
        else:
            reservations = self._conn.get_all_instances(filters={'client-token': self.client_token})
            if len(reservations) > 0:
                instance = reservations[0].instances[0]

        if instance:
            instance.terminate()

            # Wait until it's really terminated.
            while True:
                self.log_continue("[{0}] ".format(instance.state))
                if instance.state == "terminated": break
                time.sleep(3)
                instance.update()

        self.log_end("")

        # Destroy volumes created for this instance.
        for k, v in self.block_device_mapping.items():
            if v.get('charonDeleteOnTermination', False):
                self._delete_volume(v['volumeId'])
                self.update_block_device_mapping(k, None)

        return True


    def stop(self):
        if not self._booted_from_ebs():
            self.warn("cannot stop non-EBS-backed instance")
            return

        self.log_start("stopping EC2 machine... ")

        instance = self._get_instance_by_id(self.vm_id)
        instance.stop()  # no-op if the machine is already stopped

        self.state = self.STOPPING

        # Wait until it's really stopped.
        def check_stopped():
            self.log_continue("[{0}] ".format(instance.state))
            if instance.state == "stopped":
                return True
            if instance.state not in {"running", "stopping"}:
                raise Exception(
                    "EC2 instance ‘{0}’ failed to stop (state is ‘{1}’)"
                    .format(self.vm_id, instance.state))
            instance.update()
            return False

        if not nixops.util.check_wait(check_stopped, initial=3, max_tries=300, exception=False): # = 15 min
            # If stopping times out, then do an unclean shutdown.
            self.log_end("(timed out)")
            self.log_start("force-stopping EC2 machine... ")
            instance.stop(force=True)
            if not nixops.util.check_wait(check_stopped, initial=3, max_tries=100, exception=False): # = 5 min
                # Amazon docs suggest doing a force stop twice...
                self.log_end("(timed out)")
                self.log_start("force-stopping EC2 machine... ")
                instance.stop(force=True)
                nixops.util.check_wait(check_stopped, initial=3, max_tries=100) # = 5 min

        self.log_end("")

        self.state = self.STOPPED
        self.ssh_master = None


    def start(self):
        if not self._booted_from_ebs():
            return

        self.log("starting EC2 machine...")

        instance = self._get_instance_by_id(self.vm_id)
        instance.start()  # no-op if the machine is already started

        self.state = self.STARTING

        # Wait until it's really started, and obtain its new IP
        # address.  Warn the user if the IP address has changed (which
        # is generally the case).
        prev_private_ipv4 = self.private_ipv4
        prev_public_ipv4 = self.public_ipv4

        if self.elastic_ipv4:
            self.log("restoring previously attached elastic IP")
            self.assign_elastic_ip(self.elastic_ipv4, instance, True)

        self._wait_for_ip(instance)

        if prev_private_ipv4 != self.private_ipv4 or prev_public_ipv4 != self.public_ipv4:
            self.warn("IP address has changed, you may need to run ‘nixops deploy’")

        self.wait_for_ssh(check=True)
        self.send_keys()


    def _check(self, res):
        if not self.vm_id:
            res.exists = False
            return

        self.connect()
        instance = self._get_instance_by_id(self.vm_id, allow_missing=True)
        old_state = self.state
        #self.log("instance state is ‘{0}’".format(instance.state if instance else "gone"))

        if instance is None or instance.state in {"shutting-down", "terminated"}:
            self.state = self.MISSING
            return

        res.exists = True
        if instance.state == "pending":
            res.is_up = False
            self.state = self.STARTING

        elif instance.state == "running":
            res.is_up = True

            res.disks_ok = True
            for k, v in self.block_device_mapping.items():
                if k not in instance.block_device_mapping.keys() and v.get('volumeId', None):
                    res.disks_ok = False
                    res.messages.append("volume ‘{0}’ not attached to ‘{1}’".format(v['volumeId'], _sd_to_xvd(k)))
                    volume = nixops.ec2_utils.get_volume_by_id(self.connect(), v['volumeId'], allow_missing=True)
                    if not volume:
                        res.messages.append("volume ‘{0}’ no longer exists".format(v['volumeId']))

                if k in instance.block_device_mapping.keys() and instance.block_device_mapping[k].status != 'attached' :
                    res.disks_ok = False
                    res.messages.append("volume ‘{0}’ on device ‘{1}’ has unexpected state: ‘{2}’".format(v['volumeId'], _sd_to_xvd(k), instance.block_device_mapping[k].status))


            if self.private_ipv4 != instance.private_ip_address or self.public_ipv4 != instance.ip_address:
                self.warn("IP address has changed, you may need to run ‘nixops deploy’")
                self.private_ipv4 = instance.private_ip_address
                self.public_ipv4 = instance.ip_address

            MachineState._check(self, res)

        elif instance.state == "stopping":
            res.is_up = False
            self.state = self.STOPPING

        elif instance.state == "stopped":
            res.is_up = False
            self.state = self.STOPPED

        # check for scheduled events
        instance_status = self._conn.get_all_instance_status(instance_ids=[instance.id])
        for ist in instance_status:
            if ist.events:
                for e in ist.events:
                    res.messages.append("Event ‘{0}’:".format(e.code))
                    res.messages.append("  * {0}".format(e.description))
                    res.messages.append("  * {0} - {1}".format(e.not_before, e.not_after))


    def reboot(self, hard=False):
        self.log("rebooting EC2 machine...")
        instance = self._get_instance_by_id(self.vm_id)
        instance.reboot()
        self.state = self.STARTING


    def get_console_output(self):
        if not self.vm_id:
            raise Exception("cannot get console output of non-existant machine ‘{0}’".format(self.name))
        self.connect()
        return self._conn.get_console_output(self.vm_id).output or "(not available)"


def _xvd_to_sd(dev):
    return dev.replace("/dev/xvd", "/dev/sd")


def _sd_to_xvd(dev):
    return dev.replace("/dev/sd", "/dev/xvd")

########NEW FILE########
__FILENAME__ = hetzner
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import socket
import struct
import subprocess

from hetzner.robot import Robot

from nixops import known_hosts
from nixops.util import wait_for_tcp_port, ping_tcp_port
from nixops.util import attr_property, create_key_pair
from nixops.ssh_util import SSHCommandFailed
from nixops.backends import MachineDefinition, MachineState
from nixops.nix_expr import nix2py

# This is set to True by tests/hetzner-backend.nix. If it's in effect, no
# attempt is made to connect to the real Robot API and the API calls only
# return dummy objects.
TEST_MODE = False


class TestModeServer(object):
    """
    Server object from the Hetzner API but mocked up to return only dummy
    values.
    """
    reboot = lambda s, method: None
    set_name = lambda s, name: None

    class admin(object):
        create = classmethod(lambda cls: ('test_user', 'test_pass'))
        delete = classmethod(lambda cls: None)

    class rescue(object):
        activate = classmethod(lambda cls: None)
        password = "abcd1234"


class HetznerDefinition(MachineDefinition):
    """
    Definition of a Hetzner machine.
    """
    @classmethod
    def get_type(cls):
        return "hetzner"

    def __init__(self, xml):
        MachineDefinition.__init__(self, xml)
        x = xml.find("attrs/attr[@name='hetzner']/attrs")
        assert x is not None
        for var, name, valtype in [("main_ipv4", "mainIPv4", "string"),
                                   ("robot_user", "robotUser", "string"),
                                   ("robot_pass", "robotPass", "string"),
                                   ("partitions", "partitions", "string")]:
            attr = x.find("attr[@name='" + name + "']/" + valtype)
            setattr(self, var, attr.get("value"))


class HetznerState(MachineState):
    """
    State of a Hetzner machine.
    """
    @classmethod
    def get_type(cls):
        return "hetzner"

    state = attr_property("state", MachineState.UNKNOWN, int)

    main_ipv4 = attr_property("hetzner.mainIPv4", None)
    robot_admin_user = attr_property("hetzner.robotUser", None)
    robot_admin_pass = attr_property("hetzner.robotPass", None)
    partitions = attr_property("hetzner.partitions", None)

    just_installed = attr_property("hetzner.justInstalled", False, bool)
    rescue_passwd = attr_property("hetzner.rescuePasswd", None)
    fs_info = attr_property("hetzner.fsInfo", None)
    net_info = attr_property("hetzner.networkInfo", None, 'json')
    hw_info = attr_property("hetzner.hardwareInfo", None)

    main_ssh_private_key = attr_property("hetzner.sshPrivateKey", None)
    main_ssh_public_key = attr_property("hetzner.sshPublicKey", None)

    def __init__(self, depl, name, id):
        MachineState.__init__(self, depl, name, id)
        self._robot = None

    @property
    def resource_id(self):
        return self.vm_id

    @property
    def public_ipv4(self):
        return self.main_ipv4

    def connect(self):
        """
        Connect to the Hetzner robot by using the admin credetials in
        'self.robot_admin_user' and 'self.robot_admin_pass'.
        """
        if self._robot is not None:
            return self._robot

        self._robot = Robot(self.robot_admin_user, self.robot_admin_pass)
        return self._robot

    def _get_server_from_main_robot(self, ip, defn=None):
        """
        Fetch the server instance using the main robot user and passwords
        from the MachineDefinition passed by 'defn'. If the definition does not
        contain these credentials or is None, it is tried to fetch it from
        environment variables.
        """
        if defn is not None and len(defn.robot_user) > 0:
            robot_user = defn.robot_user
        else:
            robot_user = os.environ.get('HETZNER_ROBOT_USER', None)

        if defn is not None and len(defn.robot_pass) > 0:
            robot_pass = defn.robot_pass
        else:
            robot_pass = os.environ.get('HETZNER_ROBOT_PASS', None)

        if robot_user is None:
            raise Exception("please either set ‘deployment.hetzner.robotUser’"
                            " or $HETZNER_ROBOT_USER for machine"
                            " ‘{0}’".format(self.name))
        elif robot_pass is None:
            raise Exception("please either set ‘deployment.hetzner.robotPass’"
                            " or $HETZNER_ROBOT_PASS for machine"
                            " ‘{0}’".format(self.name))

        if TEST_MODE:
            return TestModeServer()

        robot = Robot(robot_user, robot_pass)
        return robot.servers.get(ip)

    def _get_server_by_ip(self, ip):
        """
        Queries the robot for the given ip address and returns the Server
        instance if it was found.
        """
        if TEST_MODE:
            return TestModeServer()

        robot = self.connect()
        return robot.servers.get(ip)

    def get_ssh_private_key_file(self):
        if self._ssh_private_key_file:
            return self._ssh_private_key_file
        else:
            return self.write_ssh_private_key(self.main_ssh_private_key)

    def get_ssh_flags(self):
        if self.state == self.RESCUE:
            return ["-o", "LogLevel=quiet"]
        else:
            # XXX: Disabling strict host key checking will only impact the
            # behaviour on *new* keys, so it should be "reasonably" safe to do
            # this until we have a better way of managing host keys in
            # ssh_util. So far this at least avoids to accept every damn host
            # key on a large deployment.
            return ["-o", "StrictHostKeyChecking=no",
                    "-i", self.get_ssh_private_key_file()]

    def _wait_for_rescue(self, ip):
        if not TEST_MODE:
            # In test mode, the target machine really doesn't go down at all,
            # so only wait for the reboot to finish when deploying real
            # systems.
            self.log_start("waiting for rescue system...")
            dotlog = lambda: self.log_continue(".")
            wait_for_tcp_port(ip, 22, open=False, callback=dotlog)
            self.log_continue("[down]")
            wait_for_tcp_port(ip, 22, callback=dotlog)
            self.log_end("[up]")
        self.state = self.RESCUE

    def _bootstrap_rescue(self, install, partitions):
        """
        Bootstrap everything needed in order to get Nix and the partitioner
        usable in the rescue system. The keyword arguments are only for
        partitioning, see reboot_rescue() for description, if not given we will
        only mount based on information provided in self.partitions.
        """
        self.log_start("building Nix bootstrap installer...")
        expr = os.path.join(self.depl.expr_path, "hetzner-bootstrap.nix")
        bootstrap_out = subprocess.check_output(["nix-build", expr,
                                                 "--no-out-link"]).rstrip()
        bootstrap = os.path.join(bootstrap_out, 'bin/hetzner-bootstrap')
        self.log_end("done. ({0})".format(bootstrap))

        self.log_start("checking if tmpfs in rescue system is large enough...")
        dfstat = self.run_command("stat -f -c '%a:%S' /", capture_stdout=True)
        df, bs = dfstat.split(':')
        free_mb = (int(df) * int(bs)) // 1024 // 1024
        if free_mb > 300:
            self.log_end("yes: {0} MB".format(free_mb))
            tarcmd = 'tar x -C /'
        else:
            self.log_end("no: {0} MB".format(free_mb))
            tarexcludes = ['*/include', '*/man', '*/info', '*/locale',
                           '*/locales', '*/share/doc', '*/share/aclocal',
                           '*/example', '*/terminfo', '*/pkgconfig',
                           '*/nix-support', '*/etc', '*/bash-completion',
                           '*.a', '*.la', '*.pc', '*.lisp', '*.pod', '*.html',
                           '*.pyc', '*.pyo', '*-kbd-*/share', '*-gcc-*/bin',
                           '*-gcc-*/libexec', '*-systemd-*/bin',
                           '*-boehm-gc-*/share']
            tarcmd = 'tar x -C / ' + ' '.join(["--exclude='{0}'".format(glob)
                                               for glob in tarexcludes])

        # The command to retrieve our split TAR archive on the other side.
        recv = 'read -d: tarsize; head -c "$tarsize" | {0}; {0}'.format(tarcmd)

        self.log_start("copying bootstrap files to rescue system...")
        tarstream = subprocess.Popen([bootstrap], stdout=subprocess.PIPE)
        if not self.has_really_fast_connection():
            stream = subprocess.Popen(["gzip", "-c"], stdin=tarstream.stdout,
                                      stdout=subprocess.PIPE)
            self.run_command("gzip -d | ({0})".format(recv),
                             stdin=stream.stdout)
            stream.wait()
        else:
            self.run_command(recv, stdin=tarstream.stdout)
        tarstream.wait()
        self.log_end("done.")

        if install:
            self.log_start("partitioning disks...")
            try:
                out = self.run_command("nixpart -p -", capture_stdout=True,
                                       stdin_string=partitions)
            except SSHCommandFailed as cmd:
                # Exit code 100 is when the partitioner requires a reboot.
                if cmd.exitcode == 100:
                    self.log(cmd.message)
                    self.reboot_rescue(install, partitions)
                    return
                else:
                    raise

            # This is the *only* place to set self.partitions unless we have
            # implemented a way to repartition the system!
            self.partitions = partitions
            self.fs_info = out
        else:
            self.log_start("mounting filesystems...")
            self.run_command("nixpart -m -", stdin_string=self.partitions)
        self.log_end("done.")

        if not install:
            self.log_start("checking if system in /mnt is NixOS...")
            res = self.run_command("test -e /mnt/etc/NIXOS", check=False)
            if res == 0:
                self.log_end("yes.")
            else:
                self.log_end("NO! Not mounting special filesystems.")
                return

        self.log_start("bind-mounting special filesystems...")
        for mountpoint in ("/proc", "/dev", "/dev/shm", "/sys"):
            self.log_continue("{0}...".format(mountpoint))
            cmd = "mkdir -m 0755 -p /mnt{0} && ".format(mountpoint)
            cmd += "mount --bind {0} /mnt{0}".format(mountpoint)
            self.run_command(cmd)
        self.log_end("done.")

    def reboot(self, hard=False):
        if hard:
            self.log_start("sending hard reset to robot...")
            server = self._get_server_by_ip(self.main_ipv4)
            server.reboot('hard')
            self.log_end("done.")
            self.state = self.STARTING
            self.ssh.reset()
        else:
            MachineState.reboot(self, hard=hard)

    def reboot_rescue(self, install=False, partitions=None, bootstrap=True,
                      hard=False):
        """
        Use the Robot to activate the rescue system and reboot the system. By
        default, only mount partitions and do not partition or wipe anything.

        On installation, both 'installed' has to be set to True and partitions
        should contain a Kickstart configuration, otherwise it's read from
        self.partitions if available (which it shouldn't if you're not doing
        something nasty).
        """
        self.log("rebooting machine ‘{0}’ ({1}) into rescue system"
                 .format(self.name, self.main_ipv4))
        server = self._get_server_by_ip(self.main_ipv4)
        server.rescue.activate()
        rescue_passwd = server.rescue.password
        if hard or (install and self.state not in (self.UP, self.RESCUE)):
            self.log_start("sending hard reset to robot...")
            server.reboot('hard')
        else:
            self.log_start("sending reboot command...")
            if self.state == self.RESCUE:
                self.run_command("(sleep 2; reboot) &", check=False)
            else:
                self.run_command("systemctl reboot", check=False)
        self.log_end("done.")
        self._wait_for_rescue(self.main_ipv4)
        self.rescue_passwd = rescue_passwd
        self.state = self.RESCUE
        self.ssh.reset()
        if bootstrap:
            self._bootstrap_rescue(install, partitions)

    def _install_main_ssh_keys(self):
        """
        Create a SSH private/public keypair and put the public key into the
        chroot.
        """
        private, public = create_key_pair(
            key_name="NixOps client key of {0}".format(self.name)
        )
        self.main_ssh_private_key, self.main_ssh_public_key = private, public
        res = self.run_command("umask 077 && mkdir -p /mnt/root/.ssh &&"
                               " cat > /mnt/root/.ssh/authorized_keys",
                               stdin_string=public)

    def _install_base_system(self):
        self.log_start("creating missing directories...")
        cmds = ["mkdir -m 1777 -p /mnt/tmp /mnt/nix/store"]
        mntdirs = ["var", "etc", "bin", "nix/var/nix/gcroots",
                   "nix/var/nix/temproots", "nix/var/nix/manifests",
                   "nix/var/nix/userpool", "nix/var/nix/profiles",
                   "nix/var/nix/db", "nix/var/log/nix/drvs"]
        to_create = ' '.join(map(lambda d: os.path.join("/mnt", d), mntdirs))
        cmds.append("mkdir -m 0755 -p {0}".format(to_create))
        self.run_command(' && '.join(cmds))
        self.log_end("done.")

        self.log_start("bind-mounting files in /etc...")
        for etcfile in ("resolv.conf", "passwd", "group"):
            self.log_continue("{0}...".format(etcfile))
            cmd = ("if ! test -e /mnt/etc/{0}; then"
                   " touch /mnt/etc/{0} && mount --bind /etc/{0} /mnt/etc/{0};"
                   " fi").format(etcfile)
            self.run_command(cmd)
        self.log_end("done.")

        self.run_command("touch /mnt/etc/NIXOS")
        self.run_command("activate-remote")
        self._install_main_ssh_keys()
        self._gen_network_spec()

    def _detect_hardware(self):
        self.log_start("detecting hardware...")
        cmd = "nixos-generate-config --no-filesystems --show-hardware-config"
        hardware = self.run_command(cmd, capture_stdout=True)
        self.hw_info = '\n'.join([line for line in hardware.splitlines()
                                  if not line.rstrip().startswith('#')])
        self.log_end("done.")

    def switch_to_configuration(self, method, sync, command=None):
        if self.state == self.RESCUE:
            # We cannot use the mountpoint command here, because it's unable to
            # detect bind mounts on files, so we just go ahead and try to
            # unmount.
            umount = 'if umount "{0}" 2> /dev/null; then rm -f "{0}"; fi'
            cmd = '; '.join([umount.format(os.path.join("/mnt/etc", mnt))
                             for mnt in ("resolv.conf", "passwd", "group")])
            self.run_command(cmd)

            command = "chroot /mnt /nix/var/nix/profiles/system/bin/"
            command += "switch-to-configuration"

        res = MachineState.switch_to_configuration(self, method, sync, command)
        if res not in (0, 100):
            return res
        if self.state == self.RESCUE and self.just_installed:
            self.reboot_sync()
            self.just_installed = False
        return res

    def _get_ethernet_interfaces(self):
        """
        Return a list of all the ethernet interfaces active on the machine.
        """
        # We don't use \(\) here to ensure this works even without GNU sed.
        cmd = "ip addr show | sed -n -e 's/^[0-9]*: *//p' | cut -d: -f1"
        return self.run_command(cmd, capture_stdout=True).splitlines()

    def _get_udev_rule_for(self, interface):
        """
        Get lines suitable for services.udev.extraRules for 'interface',
        and thus essentially map the device name to a hardware address.
        """
        cmd = "ip addr show \"{0}\" | sed -n -e 's|^.*link/ether  *||p'"
        cmd += " | cut -d' ' -f1"
        mac_addr = self.run_command(cmd.format(interface),
                                    capture_stdout=True).strip()

        rule = 'ACTION=="add", SUBSYSTEM=="net", ATTR{{address}}=="{0}", '
        rule += 'NAME="{1}"'
        return rule.format(mac_addr, interface)

    def _get_ipv4_addr_and_prefix_for(self, interface):
        """
        Return a tuple of (ipv4_address, prefix_length) for the specified
        interface.
        """
        cmd = "ip addr show \"{0}\" | sed -n -e 's/^.*inet  *//p'"
        cmd += " | cut -d' ' -f1"
        ipv4_addr_prefix = self.run_command(cmd.format(interface),
                                            capture_stdout=True).strip()
        if "/" not in ipv4_addr_prefix:
            # No IP address set for this interface.
            return None
        else:
            return ipv4_addr_prefix.split('/', 1)

    def _get_default_gw(self):
        """
        Return the default gateway of the currently running machine.
        """
        cmd = "ip route list | sed -n -e 's/^default  *via  *//p'"
        cmd += " | cut -d' ' -f1"
        return self.run_command(cmd, capture_stdout=True).strip()

    def _get_nameservers(self):
        """
        Return a list of all nameservers defined on the currently running
        machine.
        """
        cmd = "cat /etc/resolv.conf | sed -n -e 's/^nameserver  *//p'"
        return self.run_command(cmd, capture_stdout=True).splitlines()

    def _indent(self, lines, level=1):
        """
        Indent list of lines by the specified level (one level = two spaces).
        """
        return map(lambda line: "  " + line, lines)

    def _calculate_ipv4_subnet(self, ipv4, prefix_len):
        """
        Returns the address of the subnet for the given 'ipv4' and
        'prefix_len'.
        """
        bits = struct.unpack('!L', socket.inet_aton(ipv4))[0]
        mask = 0xffffffff >> (32 - prefix_len) << (32 - prefix_len)
        return socket.inet_ntoa(struct.pack('!L', bits & mask))

    def _gen_network_spec(self):
        """
        Generate Nix expressions related to networking configuration based on
        the currently running machine (most likely in RESCUE state) and set the
        resulting string to self.net_info.
        """
        udev_rules = []
        iface_attrs = {}
        extra_routes = []
        ipv6_commands = []

        server = self._get_server_by_ip(self.main_ipv4)

        # Global networking options
        defgw = self._get_default_gw()
        v6defgw = None

        # Interface-specific networking options
        for iface in self._get_ethernet_interfaces():
            if iface == "lo":
                continue

            result = self._get_ipv4_addr_and_prefix_for(iface)
            if result is None:
                continue

            udev_rules.append(self._get_udev_rule_for(iface))

            ipv4, prefix = result
            iface_attrs[iface] = {
                'ipAddress': ipv4,
                'prefixLength': int(prefix),
            }

            # We can't handle Hetzner-specific networking info in test mode.
            if TEST_MODE:
                continue

            # Extra route for accessing own subnet
            net = self._calculate_ipv4_subnet(ipv4, int(prefix))
            extra_routes.append(("{0}/{1}".format(net, prefix), defgw, iface))

            # IPv6 subnets only for eth0 (XXX: more flexibility here?)
            v6addr_command = "ip -6 addr add '{0}' dev '{1}' || true"
            for subnet in server.subnets:
                if "." in subnet.net_ip:
                    # skip IPv4 addresses
                    continue
                v6addr = "{0}/{1}".format(subnet.net_ip, subnet.mask)
                ipv6_commands.append(v6addr_command.format(v6addr, iface))
                assert v6defgw is None or v6defgw == subnet.gateway
                v6defgw = subnet.gateway

        # Extra routes
        route4_cmd = "ip -4 route change '{0}' via '{1}' dev '{2}' || true"
        route_commands = [route4_cmd.format(net, gw, iface)
                          for net, gw, iface in extra_routes]

        # IPv6 configuration
        route6_cmd = "ip -6 route add default via '{0}' dev eth0 || true"
        route_commands.append(route6_cmd.format(v6defgw))

        local_commands = '\n'.join(ipv6_commands + route_commands) + '\n'

        self.net_info = {
            'services': {
                'udev': {'extraRules': '\n'.join(udev_rules) + '\n'},
            },
            'networking': {
                'interfaces': iface_attrs,
                'defaultGateway': defgw,
                'nameservers': self._get_nameservers(),
                'localCommands': local_commands,
            }
        }

    def get_physical_spec(self):
        if all([self.net_info, self.fs_info, self.hw_info]):
            return {
                'config': self.net_info,
                'imports': [nix2py(self.fs_info), nix2py(self.hw_info)],
            }
        else:
            return {}

    def create(self, defn, check, allow_reboot, allow_recreate):
        assert isinstance(defn, HetznerDefinition)

        if self.state not in (self.RESCUE, self.UP) or check:
            self.check()

        self.set_common_state(defn)
        self.main_ipv4 = defn.main_ipv4

        if not self.robot_admin_user or not self.robot_admin_pass:
            self.log_start("creating an exclusive robot admin account for "
                           "‘{0}’...".format(self.name))
            # Create a new Admin account exclusively for this machine.
            server = self._get_server_from_main_robot(self.main_ipv4, defn)
            with self.depl._db:
                (self.robot_admin_user,
                 self.robot_admin_pass) = server.admin.create()
            self.log_end("done. ({0})".format(self.robot_admin_user))

        if not self.vm_id:
            self.log("installing machine...")
            self.reboot_rescue(install=True, partitions=defn.partitions)
            self._install_base_system()
            self._detect_hardware()
            server = self._get_server_by_ip(self.main_ipv4)
            vm_id = "nixops-{0}-{1}".format(self.depl.uuid, self.name)
            server.set_name(vm_id[:100])
            self.vm_id = vm_id
            known_hosts.remove(self.main_ipv4)
            self.just_installed = True

    def start(self):
        """
        Start the server into the normal system (a reboot is done if the rescue
        system is active).
        """
        if self.state == self.UP:
            return
        elif self.state == self.RESCUE:
            self.reboot()
        elif self.state in (self.STOPPED, self.UNREACHABLE):
            self.log_start("server was shut down, sending hard reset...")
            server = self._get_server_by_ip(self.main_ipv4)
            server.reboot("hard")
            self.log_end("done.")
            self.state = self.STARTING
        self.wait_for_ssh(check=True)
        self.send_keys()

    def _wait_stop(self):
        """
        Wait for the system to shutdown and set state STOPPED afterwards.
        """
        self.log_start("waiting for system to shutdown...")
        dotlog = lambda: self.log_continue(".")
        wait_for_tcp_port(self.main_ipv4, 22, open=False, callback=dotlog)
        self.log_continue("[down]")

        self.state = self.STOPPED

    def stop(self):
        """
        Stops the server by shutting it down without powering it off.
        """
        if self.state not in (self.RESCUE, self.UP):
            return
        self.log_start("shutting down system...")
        self.run_command("systemctl halt", check=False)
        self.log_end("done.")

        self.state = self.STOPPING
        self._wait_stop()

    def get_ssh_name(self):
        assert self.main_ipv4
        return self.main_ipv4

    def get_ssh_password(self):
        if self.state == self.RESCUE:
            return self.rescue_passwd
        else:
            return None

    def _check(self, res):
        if not self.vm_id:
            res.exists = False
            return

        if self.state in (self.STOPPED, self.STOPPING):
            res.is_up = ping_tcp_port(self.main_ipv4, 22)
            if not res.is_up:
                self.state = self.STOPPED
                res.is_reachable = False
                return

        res.exists = True
        avg = self.get_load_avg()
        if avg is None:
            if self.state in (self.UP, self.RESCUE):
                self.state = self.UNREACHABLE
            res.is_reachable = False
            res.is_up = False
        elif self.run_command("test -f /etc/NIXOS", check=False) != 0:
            self.state = self.RESCUE
            self.ssh_pinged = True
            self._ssh_pinged_this_time = True
            res.is_reachable = True
            res.is_up = False
        else:
            res.is_up = True
            MachineState._check(self, res)

    def _destroy(self, server, wipe):
        if self.state != self.RESCUE:
            self.reboot_rescue(bootstrap=False, hard=True)
        if wipe:
            self.log_start("erasing all data on disk...")
            # Let it run in the background because it will take a long time.
            cmd = "nohup shred /dev/[sh]d? &> /dev/null < /dev/null &"
            self.run_command(cmd)
            self.log_end("done. (backgrounded)")
        self.log_start("unsetting server name...")
        server.set_name("")
        self.log_end("done.")
        self.log_start("removing admin account...")
        server.admin.delete()
        self.log_start("done.")
        self.log("machine left in rescue, password: "
                 "{0}".format(self.rescue_passwd))
        return True

    def destroy(self, wipe=False):
        if not self.vm_id:
            return True

        # Create the instance as early as possible because if we don't have the
        # needed credentials, we really don't have to even ask for destruction.
        server = self._get_server_from_main_robot(self.main_ipv4)

        if wipe:
            question = "are you sure you want to completely erase {0}?"
        else:
            question = "are you sure you want to destroy {0}?"
        question_target = "Hetzner machine ‘{0}’?".format(self.name)
        if not self.depl.logger.confirm(question.format(question_target)):
            return False

        return self._destroy(server, wipe)

########NEW FILE########
__FILENAME__ = none
# -*- coding: utf-8 -*-

from nixops.backends import MachineDefinition, MachineState
import nixops.util
import sys

class NoneDefinition(MachineDefinition):
    """Definition of a trivial machine."""

    @classmethod
    def get_type(cls):
        return "none"

    def __init__(self, xml):
        MachineDefinition.__init__(self, xml)
        self._target_host = xml.find("attrs/attr[@name='targetHost']/string").get("value")


class NoneState(MachineState):
    """State of a trivial machine."""

    @classmethod
    def get_type(cls):
        return "none"

    target_host = nixops.util.attr_property("targetHost", None)

    def __init__(self, depl, name, id):
        MachineState.__init__(self, depl, name, id)

    def create(self, defn, check, allow_reboot, allow_recreate):
        assert isinstance(defn, NoneDefinition)
        self.set_common_state(defn)
        self.target_host = defn._target_host

    def get_ssh_name(self):
        assert self.target_host
        return self.target_host

    def _check(self, res):
        res.exists = True # can't really check
        res.is_up = nixops.util.ping_tcp_port(self.target_host, 22)
        if res.is_up:
            MachineState._check(self, res)

    def destroy(self, wipe=False):
        # No-op; just forget about the machine.
        return True

########NEW FILE########
__FILENAME__ = virtualbox
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import stat
from nixops.backends import MachineDefinition, MachineState
from nixops.nix_expr import RawValue
import nixops.known_hosts
from distutils import spawn

sata_ports = 8


class VirtualBoxDefinition(MachineDefinition):
    """Definition of a VirtualBox machine."""

    @classmethod
    def get_type(cls):
        return "virtualbox"

    def __init__(self, xml):
        MachineDefinition.__init__(self, xml)
        x = xml.find("attrs/attr[@name='virtualbox']/attrs")
        assert x is not None
        self.memory_size = x.find("attr[@name='memorySize']/int").get("value")
        self.headless = x.find("attr[@name='headless']/bool").get("value") == "true"

        def f(xml):
            return {'port': int(xml.find("attrs/attr[@name='port']/int").get("value")),
                    'size': int(xml.find("attrs/attr[@name='size']/int").get("value")),
                    'baseImage': xml.find("attrs/attr[@name='baseImage']/string").get("value")}

        self.disks = {k.get("name"): f(k) for k in x.findall("attr[@name='disks']/attrs/attr")}

        def sf(xml):
            return {'hostPath': xml.find("attrs/attr[@name='hostPath']/string").get("value"),
                    'readOnly': xml.find("attrs/attr[@name='readOnly']/bool").get("value") == "true"}

        self.shared_folders = {k.get("name"): sf(k) for k in x.findall("attr[@name='sharedFolders']/attrs/attr")}


class VirtualBoxState(MachineState):
    """State of a VirtualBox machine."""

    @classmethod
    def get_type(cls):
        return "virtualbox"

    state = nixops.util.attr_property("state", MachineState.MISSING, int) # override
    private_ipv4 = nixops.util.attr_property("privateIpv4", None)
    disks = nixops.util.attr_property("virtualbox.disks", {}, 'json')
    _client_private_key = nixops.util.attr_property("virtualbox.clientPrivateKey", None)
    _client_public_key = nixops.util.attr_property("virtualbox.clientPublicKey", None)
    _headless = nixops.util.attr_property("virtualbox.headless", False, bool)
    sata_controller_created = nixops.util.attr_property("virtualbox.sataControllerCreated", False, bool)
    public_host_key = nixops.util.attr_property("virtualbox.publicHostKey", None)
    private_host_key = nixops.util.attr_property("virtualbox.privateHostKey", None)
    shared_folders = nixops.util.attr_property("virtualbox.sharedFolders", {}, 'json')

    # Obsolete.
    disk = nixops.util.attr_property("virtualbox.disk", None)
    disk_attached = nixops.util.attr_property("virtualbox.diskAttached", False, bool)

    def __init__(self, depl, name, id):
        MachineState.__init__(self, depl, name, id)
        self._disk_attached = False

    @property
    def resource_id(self):
        return self.vm_id

    def get_ssh_name(self):
        assert self.private_ipv4
        return self.private_ipv4

    def get_ssh_private_key_file(self):
        return self._ssh_private_key_file or self.write_ssh_private_key(self._client_private_key)

    def get_ssh_flags(self):
        return ["-o", "StrictHostKeyChecking=no", "-i", self.get_ssh_private_key_file()]

    def get_physical_spec(self):
        return {'require': [RawValue('<nixops/virtualbox-image-nixops.nix>')]}


    def address_to(self, m):
        if isinstance(m, VirtualBoxState):
            return m.private_ipv4
        return MachineState.address_to(self, m)


    def has_really_fast_connection(self):
        return True

    @property
    def _vbox_version(self):
        v = getattr(self, '_vbox_version_obj', None)
        if v is None:
            try:
                v = self._logged_exec(["VBoxManage", "--version"], capture_stdout=True, check=False).strip().split('.')
            except AttributeError:
                v = False
            self._vbox_version_obj = v
        return v

    @property
    def _vbox_flag_sataportcount(self):
        v = self._vbox_version
        return '--portcount' if (int(v[0]) >= 4 and int(v[1]) >= 3) else '--sataportcount'

    def _get_vm_info(self, can_fail=False):
        '''Return the output of ‘VBoxManage showvminfo’ in a dictionary.'''
        lines = self._logged_exec(
            ["VBoxManage", "showvminfo", "--machinereadable", self.vm_id],
            capture_stdout=True, check=False).splitlines()
        # We ignore the exit code, because it may be 1 while the VM is
        # shutting down (even though the necessary info is returned on
        # stdout).
        if len(lines) == 0:
            if can_fail:
                return None
            raise Exception("unable to get info on VirtualBox VM ‘{0}’".format(self.name))
        vminfo = {}
        for l in lines:
            (k, v) = l.split("=", 1)
            vminfo[k] = v if v[0]!='"' else v[1:-1]
        return vminfo


    def _get_vm_state(self, can_fail=False):
        '''Return the state ("running", etc.) of a VM.'''
        vminfo = self._get_vm_info(can_fail)
        if not vminfo and can_fail:
            return None
        if 'VMState' not in vminfo:
            raise Exception("unable to get state of VirtualBox VM ‘{0}’".format(self.name))
        return vminfo['VMState'].replace('"', '')


    def _start(self):
        self._logged_exec(
            ["VBoxManage", "guestproperty", "set", self.vm_id, "/VirtualBox/GuestInfo/Net/1/V4/IP", ''])

        self._logged_exec(
            ["VBoxManage", "guestproperty", "set", self.vm_id, "/VirtualBox/GuestInfo/Charon/ClientPublicKey", self._client_public_key])

        self._logged_exec(["VBoxManage", "startvm", self.vm_id] +
                          (["--type", "headless"] if self._headless else []))

        self.state = self.STARTING


    def _update_ip(self):
        res = self._logged_exec(
            ["VBoxManage", "guestproperty", "get", self.vm_id, "/VirtualBox/GuestInfo/Net/1/V4/IP"],
            capture_stdout=True).rstrip()
        if res[0:7] != "Value: ": return
        self.private_ipv4 = res[7:]


    def _update_disk(self, name, state):
        disks = self.disks
        if state == None:
            disks.pop(name, None)
        else:
            disks[name] = state
        self.disks = disks


    def _update_shared_folder(self, name, state):
        shared_folders = self.shared_folders
        if state == None:
            shared_folders.pop(name, None)
        else:
            shared_folders[name] = state
        self.shared_folders = shared_folders


    def _wait_for_ip(self):
        self.log_start("waiting for IP address...")
        while True:
            self._update_ip()
            if self.private_ipv4 != None: break
            time.sleep(1)
            self.log_continue(".")
        self.log_end(" " + self.private_ipv4)
        nixops.known_hosts.remove(self.private_ipv4)


    def create(self, defn, check, allow_reboot, allow_recreate):
        assert isinstance(defn, VirtualBoxDefinition)

        if self.state != self.UP or check: self.check()

        self.set_common_state(defn)

        # check if VBoxManage is available in PATH
        if not spawn.find_executable("VBoxManage"):
            raise Exception("VirtualBox is not installed, please install VirtualBox.")

        if not self.vm_id:
            self.log("creating VirtualBox VM...")
            vm_id = "nixops-{0}-{1}".format(self.depl.uuid, self.name)
            self._logged_exec(["VBoxManage", "createvm", "--name", vm_id, "--ostype", "Linux26_64", "--register"])
            self.vm_id = vm_id
            self.state = self.STOPPED

        # Generate a public/private host key.
        if not self.public_host_key:
            (private, public) = nixops.util.create_key_pair()
            with self.depl._db:
                self.public_host_key = public
                self.private_host_key = private

        self._logged_exec(
            ["VBoxManage", "guestproperty", "set", self.vm_id, "/VirtualBox/GuestInfo/Charon/PrivateHostKey", self.private_host_key])

        # Backwards compatibility.
        if self.disk:
            with self.depl._db:
                self._update_disk("disk1", {"created": True, "path": self.disk,
                                            "attached": self.disk_attached,
                                            "port": 0})
                self.disk = None
                self.sata_controller_created = self.disk_attached
                self.disk_attached = False

        # Create the SATA controller.
        if not self.sata_controller_created:
            self._logged_exec(
                ["VBoxManage", "storagectl", self.vm_id,
                 "--name", "SATA", "--add", "sata", self._vbox_flag_sataportcount, str(sata_ports),
                 "--bootable", "on", "--hostiocache", "on"])
            self.sata_controller_created = True

        vm_dir = os.path.dirname(self._get_vm_info()['CfgFile'])

        if not os.path.isdir(vm_dir):
            raise Exception("can't find directory of VirtualBox VM ‘{0}’".format(self.name))


        # Create missing shared folders
        for sf_name, sf_def in defn.shared_folders.items():
            sf_state = self.shared_folders.get(sf_name, {})

            if not sf_state.get('added', False):
                self.log("adding shared folder ‘{0}’...".format(sf_name))
                host_path = sf_def.get('hostPath')
                read_only = sf_def.get('readOnly')

                vbox_opts = ["VBoxManage", "sharedfolder", "add", self.vm_id,
                             "--name", sf_name, "--hostpath", host_path]

                if read_only:
                    vbox_opts.append("--readonly")

                self._logged_exec(vbox_opts)

                sf_state['added'] = True
                self._update_shared_folder(sf_name, sf_state)

        # Remove obsolete shared folders
        for sf_name, sf_state in self.shared_folders.items():
            if sf_name not in defn.shared_folders:
                if not self.started:
                    self.log("removing shared folder ‘{0}’".format(sf_name))

                    if sf_state['added']:
                        vbox_opts = ["VBoxManage", "sharedfolder", "remove", self.vm_id,
                                     "--name", sf_name]
                        self._logged_exec(vbox_opts)

                    self._update_shared_folder(sf_name, None)
                else:
                    self.warn("skipping removal of shared folder ‘{0}’ since VirtualBox machine is running".format(sf_name))



        # Create missing disks.
        for disk_name, disk_def in defn.disks.items():
            disk_state = self.disks.get(disk_name, {})

            if not disk_state.get('created', False):
                self.log("creating disk ‘{0}’...".format(disk_name))

                disk_path = "{0}/{1}.vdi".format(vm_dir, disk_name)

                base_image = disk_def.get('baseImage')
                if base_image:
                    # Clone an existing disk image.
                    if base_image == "drv":
                        # FIXME: move this to deployment.py.
                        base_image = self._logged_exec(
                            ["nix-build"]
                            + self.depl._eval_flags(self.depl.nix_exprs) +
                            ["--arg", "checkConfigurationOptions", "false",
                             "-A", "nodes.{0}.config.deployment.virtualbox.disks.{1}.baseImage".format(self.name, disk_name),
                             "-o", "{0}/vbox-image-{1}".format(self.depl.tempdir, self.name)],
                            capture_stdout=True).rstrip()
                    self._logged_exec(["VBoxManage", "clonehd", base_image, disk_path])
                else:
                    # Create an empty disk.
                    if disk_def['size'] <= 0:
                        raise Exception("size of VirtualBox disk ‘{0}’ must be positive".format(disk_name))
                    self._logged_exec(["VBoxManage", "createhd", "--filename", disk_path, "--size", str(disk_def['size'])])
                    disk_state['size'] = disk_def['size']

                disk_state['created'] = True
                disk_state['path'] = disk_path
                self._update_disk(disk_name, disk_state)

            if not disk_state.get('attached', False):
                self.log("attaching disk ‘{0}’...".format(disk_name))

                if disk_def['port'] >= sata_ports:
                    raise Exception("SATA port number {0} of disk ‘{1}’ exceeds maximum ({2})".format(disk_def['port'], disk_name, sata_ports))

                for disk_name2, disk_state2 in self.disks.items():
                    if disk_name != disk_name2 and disk_state2.get('attached', False) and \
                            disk_state2['port'] == disk_def['port']:
                        raise Exception("cannot attach disks ‘{0}’ and ‘{1}’ to the same SATA port on VirtualBox machine ‘{2}’".format(disk_name, disk_name2, self.name))

                self._logged_exec(
                    ["VBoxManage", "storageattach", self.vm_id,
                     "--storagectl", "SATA", "--port", str(disk_def['port']), "--device", "0",
                     "--type", "hdd", "--medium", disk_state['path']])
                disk_state['attached'] = True
                disk_state['port'] = disk_def['port']
                self._update_disk(disk_name, disk_state)

        # FIXME: warn about changed disk attributes (like size).  Or
        # even better, handle them (e.g. resize existing disks).

        # Destroy obsolete disks.
        for disk_name, disk_state in self.disks.items():
            if disk_name not in defn.disks:
                if not self.depl.logger.confirm("are you sure you want to destroy disk ‘{0}’ of VirtualBox instance ‘{1}’?".format(disk_name, self.name)):
                    raise Exception("not destroying VirtualBox disk ‘{0}’".format(disk_name))
                self.log("destroying disk ‘{0}’".format(disk_name))

                if disk_state.get('attached', False):
                    # FIXME: only do this if the device is actually
                    # attached (and remove check=False).
                    self._logged_exec(
                        ["VBoxManage", "storageattach", self.vm_id,
                         "--storagectl", "SATA", "--port", str(disk_state['port']), "--device", "0",
                         "--type", "hdd", "--medium", "none"], check=False)
                    disk_state['attached'] = False
                    disk_state.pop('port')
                    self._update_disk(disk_name, disk_state)

                if disk_state['created']:
                    self._logged_exec(
                        ["VBoxManage", "closemedium", "disk", disk_state['path'], "--delete"])

                self._update_disk(disk_name, None)

        if not self._client_private_key:
            (self._client_private_key, self._client_public_key) = nixops.util.create_key_pair()

        if not self.started:
            self._logged_exec(
                ["VBoxManage", "modifyvm", self.vm_id,
                 "--memory", defn.memory_size, "--vram", "10",
                 "--nictype1", "virtio", "--nictype2", "virtio",
                 "--nic2", "hostonly", "--hostonlyadapter2", "vboxnet0",
                 "--nestedpaging", "off"])

            self._headless = defn.headless
            self._start()

        if not self.private_ipv4 or check:
            self._wait_for_ip()


    def destroy(self, wipe=False):
        if not self.vm_id: return True

        if not self.depl.logger.confirm("are you sure you want to destroy VirtualBox VM ‘{0}’?".format(self.name)): return False

        self.log("destroying VirtualBox VM...")

        vmstate = self._get_vm_state(can_fail=True)
        if vmstate is None:
            self.log("VM not found, ignored")
            self.state = self.STOPPED
            return True

        if vmstate == 'running':
            self._logged_exec(["VBoxManage", "controlvm", self.vm_id, "poweroff"], check=False)

        while self._get_vm_state() not in ['poweroff', 'aborted']:
            time.sleep(1)

        self.state = self.STOPPED

        time.sleep(1) # hack to work around "machine locked" errors

        self._logged_exec(["VBoxManage", "unregistervm", "--delete", self.vm_id])

        return True


    def stop(self):
        if self._get_vm_state() != 'running': return

        self.log_start("shutting down... ")

        self.run_command("systemctl poweroff", check=False)
        self.state = self.STOPPING

        while True:
            state = self._get_vm_state()
            self.log_continue("[{0}] ".format(state))
            if state == 'poweroff': break
            time.sleep(1)

        self.log_end("")

        self.state = self.STOPPED
        self.ssh_master = None


    def start(self):
        if self._get_vm_state() == 'running': return
        self.log("restarting...")

        prev_ipv4 = self.private_ipv4

        self._start()
        self._wait_for_ip()

        if prev_ipv4 != self.private_ipv4:
            self.warn("IP address has changed, you may need to run ‘nixops deploy’")

        self.wait_for_ssh(check=True)


    def _check(self, res):
        if not self.vm_id:
            res.exists = False
            return
        state = self._get_vm_state()
        res.exists = True
        #self.log("VM state is ‘{0}’".format(state))
        if state == "poweroff" or state == "aborted":
            res.is_up = False
            self.state = self.STOPPED
        elif state == "running":
            res.is_up = True
            self._update_ip()
            MachineState._check(self, res)
        else:
            self.state = self.UNKNOWN

########NEW FILE########
__FILENAME__ = deployment
# -*- coding: utf-8 -*-

import sys
import os.path
import subprocess
import json
import string
import tempfile
import shutil
import threading
import exceptions
import errno
from collections import defaultdict
from xml.etree import ElementTree
import nixops.statefile
import nixops.backends
import nixops.logger
import nixops.parallel
import nixops.resources.ssh_keypair
import nixops.resources.ec2_keypair
import nixops.resources.sqs_queue
import nixops.resources.iam_role
import nixops.resources.s3_bucket
import nixops.resources.ec2_security_group
import nixops.resources.ebs_volume
import nixops.resources.elastic_ip
from nixops.nix_expr import RawValue, Function, nixmerge, py2nix
import re
from datetime import datetime
import getpass
import traceback
import glob
import fcntl
import itertools
import platform

class NixEvalError(Exception):
    pass

class UnknownBackend(Exception):
    pass

debug = False

class Deployment(object):
    """NixOps top-level deployment manager."""

    default_description = "Unnamed NixOps network"

    name = nixops.util.attr_property("name", None)
    nix_exprs = nixops.util.attr_property("nixExprs", [], 'json')
    nix_path = nixops.util.attr_property("nixPath", [], 'json')
    args = nixops.util.attr_property("args", {}, 'json')
    description = nixops.util.attr_property("description", default_description)
    configs_path = nixops.util.attr_property("configsPath", None)
    rollback_enabled = nixops.util.attr_property("rollbackEnabled", False)

    def __init__(self, statefile, uuid, log_file=sys.stderr):
        self._statefile = statefile
        self._db = statefile._db
        self.uuid = uuid

        self._last_log_prefix = None
        self.extra_nix_path = []
        self.extra_nix_flags = []
        self.extra_nix_eval_flags = []
        self.nixos_version_suffix = None

        self.logger = nixops.logger.Logger(log_file)

        self._lock_file_path = None

        self.expr_path = os.path.realpath(os.path.dirname(__file__) + "/../../../../share/nix/nixops")
        if not os.path.exists(self.expr_path):
            self.expr_path = os.path.realpath(os.path.dirname(__file__) + "/../../../../../share/nix/nixops")
        if not os.path.exists(self.expr_path):
            self.expr_path = os.path.dirname(__file__) + "/../nix"

        self.tempdir = nixops.util.SelfDeletingDir(tempfile.mkdtemp(prefix="nixops-tmp"))

        self.resources = {}
        with self._db:
            c = self._db.cursor()
            c.execute("select id, name, type from Resources where deployment = ?", (self.uuid,))
            for (id, name, type) in c.fetchall():
                r = nixops.backends.create_state(self, type, name, id)
                self.resources[name] = r
        self.logger.update_log_prefixes()

        self.definitions = None


    @property
    def machines(self):
        return {n: r for n, r in self.resources.items() if is_machine(r)}

    @property
    def active(self): # FIXME: rename to "active_machines"
        return {n: r for n, r in self.resources.items() if is_machine(r) and not r.obsolete}

    @property
    def active_resources(self):
        return {n: r for n, r in self.resources.items() if not r.obsolete}


    def get_typed_resource(self, name, type):
        res = self.active_resources.get(name, None)
        if not res:
            raise Exception("resource ‘{0}’ does not exist".format(name))
        if res.get_type() != type:
            raise Exception("resource ‘{0}’ is not of type ‘{1}’".format(name, type))
        return res


    def _set_attrs(self, attrs):
        """Update deployment attributes in the state file."""
        with self._db:
            c = self._db.cursor()
            for n, v in attrs.iteritems():
                if v == None:
                    c.execute("delete from DeploymentAttrs where deployment = ? and name = ?", (self.uuid, n))
                else:
                    c.execute("insert or replace into DeploymentAttrs(deployment, name, value) values (?, ?, ?)",
                              (self.uuid, n, v))


    def _set_attr(self, name, value):
        """Update one deployment attribute in the state file."""
        self._set_attrs({name: value})


    def _del_attr(self, name):
        """Delete a deployment attribute from the state file."""
        with self._db:
            self._db.execute("delete from DeploymentAttrs where deployment = ? and name = ?", (self.uuid, name))


    def _get_attr(self, name, default=nixops.util.undefined):
        """Get a deployment attribute from the state file."""
        with self._db:
            c = self._db.cursor()
            c.execute("select value from DeploymentAttrs where deployment = ? and name = ?", (self.uuid, name))
            row = c.fetchone()
            if row != None: return row[0]
            return nixops.util.undefined


    def _create_resource(self, name, type):
        c = self._db.cursor()
        c.execute("select 1 from Resources where deployment = ? and name = ?", (self.uuid, name))
        if len(c.fetchall()) != 0:
            raise Exception("resource already exists in database!")
        c.execute("insert into Resources(deployment, name, type) values (?, ?, ?)",
                  (self.uuid, name, type))
        id = c.lastrowid
        r = nixops.backends.create_state(self, type, name, id)
        self.resources[name] = r
        return r


    def export(self):
        with self._db:
            c = self._db.cursor()
            c.execute("select name, value from DeploymentAttrs where deployment = ?", (self.uuid,))
            rows = c.fetchall()
            res = {row[0]: row[1] for row in rows}
            res['resources'] = {r.name: r.export() for r in self.resources.itervalues()}
            return res


    def import_(self, attrs):
        with self._db:
            for k, v in attrs.iteritems():
                if k == 'resources': continue
                self._set_attr(k, v)
            for k, v in attrs['resources'].iteritems():
                if 'type' not in v: raise Exception("imported resource lacks a type")
                r = self._create_resource(k, v['type'])
                r.import_(v)


    def clone(self):
        with self._db:
            new = self._statefile.create_deployment()
            self._db.execute("insert into DeploymentAttrs (deployment, name, value) " +
                             "select ?, name, value from DeploymentAttrs where deployment = ?",
                             (new.uuid, self.uuid))
            new.configs_path = None
            return new


    def _get_deployment_lock(self):
        if self._lock_file_path is None:
            lock_dir = os.environ.get("HOME", "") + "/.nixops/locks"
            if not os.path.exists(lock_dir): os.makedirs(lock_dir, 0700)
            self._lock_file_path = lock_dir + "/" + self.uuid
        class DeploymentLock(object):
            def __init__(self, depl):
                self._lock_file_path = depl._lock_file_path
                self._logger = depl.logger
                self._lock_file = None
            def __enter__(self):
                self._lock_file = open(self._lock_file_path, "w")
                fcntl.fcntl(self._lock_file, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
                try:
                    fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except IOError:
                    self._logger.log(
                        "waiting for exclusive deployment lock..."
                    )
                    fcntl.flock(self._lock_file, fcntl.LOCK_EX)
            def __exit__(self, exception_type, exception_value, exception_traceback):
                self._lock_file.close()
        return DeploymentLock(self)


    def delete_resource(self, m):
        del self.resources[m.name]
        with self._db:
            self._db.execute("delete from Resources where deployment = ? and id = ?", (self.uuid, m.id))


    def delete(self, force=False):
        """Delete this deployment from the state file."""
        with self._db:
            if not force and len(self.resources) > 0:
                raise Exception("cannot delete this deployment because it still has resources")

            # Delete the profile, if any.
            profile = self.get_profile()
            assert profile
            for p in glob.glob(profile + "*"):
                if os.path.islink(p): os.remove(p)

            # Delete the deployment from the database.
            self._db.execute("delete from Deployments where uuid = ?", (self.uuid,))


    def _nix_path_flags(self):
        flags = list(itertools.chain(*[["-I", x] for x in (self.extra_nix_path + self.nix_path)])) + self.extra_nix_flags
        flags.extend(["-I", "nixops=" + self.expr_path])
        return flags


    def _eval_flags(self, exprs):
        flags = self._nix_path_flags()
        args = {key: RawValue(val) for key, val in self.args.iteritems()}
        flags.extend(
            ["--arg", "networkExprs", py2nix(exprs, inline=True),
             "--arg", "args", py2nix(args, inline=True),
             "--argstr", "uuid", self.uuid,
             "<nixops/eval-machine-info.nix>"])
        return flags


    def set_arg(self, name, value):
        """Set a persistent argument to the deployment specification."""
        assert isinstance(name, basestring)
        assert isinstance(value, basestring)
        args = self.args
        args[name] = value
        self.args = args


    def set_argstr(self, name, value):
        """Set a persistent argument to the deployment specification."""
        assert isinstance(value, basestring)
        self.set_arg(name, py2nix(value, inline=True))


    def unset_arg(self, name):
        """Unset a persistent argument to the deployment specification."""
        assert isinstance(name, str)
        args = self.args
        args.pop(name, None)
        self.args = args


    def evaluate(self):
        """Evaluate the Nix expressions belonging to this deployment into a deployment specification."""

        self.definitions = {}

        try:
            xml = subprocess.check_output(
                ["nix-instantiate"]
                + self.extra_nix_eval_flags
                + self._eval_flags(self.nix_exprs) +
                ["--eval-only", "--xml", "--strict",
                 "--arg", "checkConfigurationOptions", "false",
                 "-A", "info"], stderr=self.logger.log_file)
            if debug: print >> sys.stderr, "XML output of nix-instantiate:\n" + xml
        except subprocess.CalledProcessError:
            raise NixEvalError

        tree = ElementTree.fromstring(xml)

        # Extract global deployment attributes.
        info = tree.find("attrs/attr[@name='network']")
        assert info != None
        elem = info.find("attrs/attr[@name='description']/string")
        self.description = elem.get("value") if elem != None else self.default_description
        elem = info.find("attrs/attr[@name='enableRollback']/bool")
        self.rollback_enabled = elem != None and elem.get("value") == "true"

        # Extract machine information.
        for x in tree.find("attrs/attr[@name='machines']/attrs").findall("attr"):
            defn = nixops.backends.create_definition(x)
            self.definitions[defn.name] = defn

        # Extract info about other kinds of resources.
        res = tree.find("attrs/attr[@name='resources']/attrs")

        for x in res.find("attr[@name='ec2KeyPairs']/attrs").findall("attr"):
            defn = nixops.resources.ec2_keypair.EC2KeyPairDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='sshKeyPairs']/attrs").findall("attr"):
            defn = nixops.resources.ssh_keypair.SSHKeyPairDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='sqsQueues']/attrs").findall("attr"):
            defn = nixops.resources.sqs_queue.SQSQueueDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='iamRoles']/attrs").findall("attr"):
            defn = nixops.resources.iam_role.IAMRoleDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='s3Buckets']/attrs").findall("attr"):
            defn = nixops.resources.s3_bucket.S3BucketDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='ec2SecurityGroups']/attrs").findall("attr"):
            defn = nixops.resources.ec2_security_group.EC2SecurityGroupDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='ebsVolumes']/attrs").findall("attr"):
            defn = nixops.resources.ebs_volume.EBSVolumeDefinition(x)
            self.definitions[defn.name] = defn

        for x in res.find("attr[@name='elasticIPs']/attrs").findall("attr"):
            defn = nixops.resources.elastic_ip.ElasticIPDefinition(x)
            self.definitions[defn.name] = defn


    def evaluate_option_value(self, machine_name, option_name, xml=False, include_physical=False):
        """Evaluate a single option of a single machine in the deployment specification."""

        exprs = self.nix_exprs
        if include_physical:
            phys_expr = self.tempdir + "/physical.nix"
            with open(phys_expr, 'w') as f:
                f.write(self.get_physical_spec())
            exprs.append(phys_expr)

        try:
            return subprocess.check_output(
                ["nix-instantiate"]
                + self.extra_nix_eval_flags
                + self._eval_flags(exprs) +
                ["--eval-only", "--strict",
                 "--arg", "checkConfigurationOptions", "false",
                 "-A", "nodes.{0}.config.{1}".format(machine_name, option_name)]
                + (["--xml"] if xml else []),
                stderr=self.logger.log_file)
        except subprocess.CalledProcessError:
            raise NixEvalError


    def get_physical_spec(self):
        """Compute the contents of the Nix expression specifying the computed physical deployment attributes"""

        active_machines = self.active
        active_resources = self.active_resources

        attrs_per_resource = {m.name: [] for m in active_resources.itervalues()}
        authorized_keys = {m.name: [] for m in active_machines.itervalues()}
        kernel_modules = {m.name: set() for m in active_machines.itervalues()}
        trusted_interfaces = {m.name: set() for m in active_machines.itervalues()}

        # Hostnames should be accumulated like this:
        #
        #   hosts[local_name][remote_ip] = [name1, name2, ...]
        #
        # This makes hosts deterministic and is more in accordance to the
        # format in hosts(5), which is like this:
        #
        #   ip_address canonical_hostname [aliases...]
        #
        # This is critical for example when using host names for access
        # control, because the canonical_hostname is returned in reverse
        # lookups.
        hosts = defaultdict(lambda: defaultdict(list))

        for m in active_machines.itervalues():
            for m2 in active_machines.itervalues():
                ip = m.address_to(m2)
                if ip:
                    hosts[m.name][ip] += [m2.name, m2.name + "-unencrypted"]
            # Always use the encrypted/unencrypted suffixes for aliases rather
            # than for the canonical name!
            hosts[m.name]["127.0.0.1"].append(m.name + "-encrypted")

        def index_to_private_ip(index):
            n = 105 + index / 256
            assert n <= 255
            return "192.168.{0}.{1}".format(n, index % 256)

        def do_machine(m):
            defn = self.definitions[m.name]
            attrs_list = attrs_per_resource[m.name]

            # Emit configuration to realise encrypted peer-to-peer links.
            for m2_name in defn.encrypted_links_to:

                if m2_name not in active_machines:
                    raise Exception("‘deployment.encryptedLinksTo’ in machine ‘{0}’ refers to an unknown machine ‘{1}’"
                                    .format(m.name, m2_name))
                m2 = active_machines[m2_name]
                # Don't create two tunnels between a pair of machines.
                if m.name in self.definitions[m2.name].encrypted_links_to and m.name >= m2.name:
                    continue
                local_ipv4 = index_to_private_ip(m.index)
                remote_ipv4 = index_to_private_ip(m2.index)
                local_tunnel = 10000 + m2.index
                remote_tunnel = 10000 + m.index
                attrs_list.append({
                    ('networking', 'p2pTunnels', 'ssh', m2.name): {
                        'target': '{0}-unencrypted'.format(m2.name),
                        'localTunnel': local_tunnel,
                        'remoteTunnel': remote_tunnel,
                        'localIPv4': local_ipv4,
                        'remoteIPv4': remote_ipv4,
                        'privateKey': '/root/.ssh/id_charon_vpn',
                    }
                })

                # FIXME: set up the authorized_key file such that ‘m’
                # can do nothing more than create a tunnel.
                authorized_keys[m2.name].append(m.public_vpn_key)
                kernel_modules[m.name].add('tun')
                kernel_modules[m2.name].add('tun')
                hosts[m.name][remote_ipv4] += [m2.name, m2.name + "-encrypted"]
                hosts[m2.name][local_ipv4] += [m.name, m.name + "-encrypted"]
                trusted_interfaces[m.name].add('tun' + str(local_tunnel))
                trusted_interfaces[m2.name].add('tun' + str(remote_tunnel))

            private_ipv4 = m.private_ipv4
            if private_ipv4:
                attrs_list.append({
                    ('networking', 'privateIPv4'): private_ipv4
                })
            public_ipv4 = m.public_ipv4
            if public_ipv4:
                attrs_list.append({
                    ('networking', 'publicIPv4'): public_ipv4
                })

            if self.nixos_version_suffix:
                attrs_list.append({
                    ('system', 'nixosVersionSuffix'): self.nixos_version_suffix
                })

        for m in active_machines.itervalues():
            do_machine(m)

        def emit_resource(r):
            config = []
            config.extend(attrs_per_resource[r.name])
            if is_machine(r):
                # Sort the hosts by its canonical host names.
                sorted_hosts = sorted(hosts[r.name].iteritems(),
                                      key=lambda item: item[1][0])
                # Just to remember the format:
                #   ip_address canonical_hostname [aliases...]
                extra_hosts = ["{0} {1}".format(ip, ' '.join(names))
                               for ip, names in sorted_hosts]

                if authorized_keys[r.name]:
                    config.append({
                        ('users', 'extraUsers', 'root'): {
                            ('openssh', 'authorizedKeys', 'keys'): authorized_keys[r.name]
                        },
                        ('services', 'openssh'): {
                            'extraConfig': "PermitTunnel yes\n"
                        },
                    })

                config.append({
                    ('boot', 'kernelModules'): list(kernel_modules[r.name]),
                    ('networking', 'firewall'): {
                        'trustedInterfaces': list(trusted_interfaces[r.name])
                    },
                    ('networking', 'extraHosts'): '\n'.join(extra_hosts) + "\n"
                })


                # Add SSH public host keys for all machines in network  
                for m2 in active_machines.itervalues():
                    if hasattr(m2, 'public_host_key') and m2.public_host_key:
                        # Using references to files in same tempdir for now, until NixOS has support
                        # for adding the keys directly as string. This way at least it is compatible
                        # with older versions of NixOS as well.
                        # TODO: after reasonable amount of time replace with string option
                        config.append({
                            ('services', 'openssh', 'knownHosts', m2.name): {
                                 'hostNames': [m2.name + "-unencrypted",
                                               m2.name + "-encrypted",
                                               m2.name],
                                 'publicKeyFile': RawValue(
                                      "./{0}.public_host_key".format(m2.name)
                                 ),
                            }
                        })

            merged = reduce(nixmerge, config) if len(config) > 0 else {}
            physical = r.get_physical_spec()

            if len(merged) == 0 and len(physical) == 0:
                return {}
            else:
                return r.prefix_definition({
                    r.name: Function("{ config, pkgs, ... }", {
                        'config': merged,
                        'imports': [physical],
                    })
                })

        return py2nix(reduce(nixmerge, [
            emit_resource(r) for r in active_resources.itervalues()
        ])) + "\n"

    def get_profile(self):
        profile_dir = "/nix/var/nix/profiles/per-user/" + getpass.getuser()
        if os.path.exists(profile_dir + "/charon") and not os.path.exists(profile_dir + "/nixops"):
            os.rename(profile_dir + "/charon", profile_dir + "/nixops")
        return profile_dir + "/nixops/" + self.uuid


    def create_profile(self):
        profile = self.get_profile()
        dir = os.path.dirname(profile)
        if not os.path.exists(dir): os.makedirs(dir, 0755)
        return profile


    def build_configs(self, include, exclude, dry_run=False, repair=False):
        """Build the machine configurations in the Nix store."""

        def write_temp_file(tmpfile, contents):
            f = open(tmpfile, "w")
            f.write(contents)
            f.close()

        self.logger.log("building all machine configurations...")

        # Set the NixOS version suffix, if we're building from Git.
        # That way ‘nixos-version’ will show something useful on the
        # target machines.
        nixos_path = subprocess.check_output(
            ["nix-instantiate", "--find-file", "nixpkgs/nixos"] + self._nix_path_flags()).rstrip()
        get_version_script = nixos_path + "/modules/installer/tools/get-version-suffix"
        if os.path.exists(nixos_path + "/.git") and os.path.exists(get_version_script):
            self.nixos_version_suffix = subprocess.check_output(["/bin/sh", get_version_script] + self._nix_path_flags()).rstrip()

        phys_expr = self.tempdir + "/physical.nix"
        p = self.get_physical_spec()
        write_temp_file(phys_expr, p)
        if debug: print >> sys.stderr, "generated physical spec:\n" + p

        for m in self.active.itervalues():
            if hasattr(m, "public_host_key") and m.public_host_key: # FIXME: use a method in MachineState.
                write_temp_file("{0}/{1}.public_host_key".format(self.tempdir, m.name), m.public_host_key + "\n")

        selected = [m for m in self.active.itervalues() if should_do(m, include, exclude)]

        names = map(lambda m: m.name, selected)

        # If we're not running on Linux, then perform the build on the
        # target machines.  FIXME: Also enable this if we're on 32-bit
        # and want to deploy to 64-bit.
        if platform.system() != 'Linux' and os.environ.get('NIX_REMOTE') != 'daemon':
            if os.environ.get('NIX_REMOTE_SYSTEMS') == None:
                remote_machines = []
                for m in sorted(selected, key=lambda m: m.index):
                    key_file = m.get_ssh_private_key_file()
                    if not key_file: raise Exception("do not know private SSH key for machine ‘{0}’".format(m.name))
                    # FIXME: Figure out the correct machine type of ‘m’ (it might not be x86_64-linux).
                    remote_machines.append("root@{0} {1} {2} 2 1\n".format(m.get_ssh_name(), 'i686-linux,x86_64-linux', key_file))
                    # Use only a single machine for now (issue #103).
                    break
                remote_machines_file = "{0}/nix.machines".format(self.tempdir)
                with open(remote_machines_file, "w") as f:
                    f.write("".join(remote_machines))
                os.environ['NIX_REMOTE_SYSTEMS'] = remote_machines_file
            else:
                self.logger.log("using predefined remote systems file: {0}".format(os.environ['NIX_REMOTE_SYSTEMS']))

            # FIXME: Use ‘--option use-build-hook true’ instead of setting
            # $NIX_BUILD_HOOK, once Nix supports that.
            os.environ['NIX_BUILD_HOOK'] = os.path.dirname(os.path.realpath(nixops.util.which("nix-build"))) + "/../libexec/nix/build-remote.pl"

            load_dir = "{0}/current-load".format(self.tempdir)
            if not os.path.exists(load_dir): os.makedirs(load_dir, 0700)
            os.environ['NIX_CURRENT_LOAD'] = load_dir

        try:
            configs_path = subprocess.check_output(
                ["nix-build"]
                + self._eval_flags(self.nix_exprs + [phys_expr]) +
                ["--arg", "names", py2nix(names, inline=True),
                 "-A", "machines", "-o", self.tempdir + "/configs"]
                + (["--dry-run"] if dry_run else [])
                + (["--repair"] if repair else []),
                stderr=self.logger.log_file).rstrip()
        except subprocess.CalledProcessError:
            raise Exception("unable to build all machine configurations")

        if self.rollback_enabled:
            profile = self.create_profile()
            if subprocess.call(["nix-env", "-p", profile, "--set", configs_path]) != 0:
                raise Exception("cannot update profile ‘{0}’".format(profile))

        return configs_path


    def copy_closures(self, configs_path, include, exclude, max_concurrent_copy):
        """Copy the closure of each machine configuration to the corresponding machine."""

        def worker(m):
            if not should_do(m, include, exclude): return
            m.logger.log("copying closure...")
            m.new_toplevel = os.path.realpath(configs_path + "/" + m.name)
            if not os.path.exists(m.new_toplevel):
                raise Exception("can't find closure of machine ‘{0}’".format(m.name))
            m.copy_closure_to(m.new_toplevel)

        nixops.parallel.run_tasks(
            nr_workers=max_concurrent_copy,
            tasks=self.active.itervalues(), worker_fun=worker)


    def activate_configs(self, configs_path, include, exclude, allow_reboot,
                         force_reboot, check, sync, always_activate):
        """Activate the new configuration on a machine."""

        def worker(m):
            if not should_do(m, include, exclude): return

            try:
                # Set the system profile to the new configuration.
                setprof = 'nix-env -p /nix/var/nix/profiles/system --set "{0}"'
                if always_activate or self.definitions[m.name].always_activate:
                    m.run_command(setprof.format(m.new_toplevel))
                else:
                    # Only activate if the profile has changed.
                    new_profile_cmd = '; '.join([
                        'old_gen="$(readlink -f /nix/var/nix/profiles/system)"',
                        'new_gen="$(readlink -f "{0}")"',
                        '[ "x$old_gen" != "x$new_gen" ] || exit 111',
                        setprof
                    ]).format(m.new_toplevel)

                    ret = m.run_command(new_profile_cmd, check=False)
                    if ret == 111:
                        m.log("configuration already up to date")
                        return
                    elif ret != 0:
                        raise Exception("unable to set new system profile")

                m.send_keys()

                if force_reboot or m.state == m.RESCUE:
                    switch_method = "boot"
                else:
                    switch_method = "switch"

                # Run the switch script.  This will also update the
                # GRUB boot loader.
                res = m.switch_to_configuration(switch_method, sync)

                if res != 0 and res != 100:
                    raise Exception("unable to activate new configuration")

                if res == 100 or force_reboot or m.state == m.RESCUE:
                    if not allow_reboot and not force_reboot:
                        raise Exception("the new configuration requires a "
                                        "reboot to take effect (hint: use "
                                        "‘--allow-reboot’)".format(m.name))
                    m.reboot_sync()
                    res = 0
                    # FIXME: should check which systemd services
                    # failed to start after the reboot.

                if res == 0:
                    m.success("activation finished successfully")

                # Record that we switched this machine to the new
                # configuration.
                m.cur_configs_path = configs_path
                m.cur_toplevel = m.new_toplevel

            except Exception as e:
                # This thread shouldn't throw an exception because
                # that will cause NixOps to exit and interrupt
                # activation on the other machines.
                m.logger.error(traceback.format_exc() if debug else str(e))
                return m.name
            return None

        res = nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active.itervalues(), worker_fun=worker)
        failed = [x for x in res if x != None]
        if failed != []:
            raise Exception("activation of {0} of {1} machines failed (namely on {2})"
                            .format(len(failed), len(res), ", ".join(["‘{0}’".format(x) for x in failed])))


    def _get_free_resource_index(self):
        index = 0
        for r in self.resources.itervalues():
            if r.index != None and index <= r.index:
                index = r.index + 1
        return index


    def get_backups(self, include=[], exclude=[]):
        self.evaluate_active(include, exclude) # unnecessary?
        machine_backups = {}
        for m in self.active.itervalues():
            if should_do(m, include, exclude):
                machine_backups[m.name] = m.get_backups()

        # merging machine backups into network backups
        backup_ids = [b for bs in machine_backups.values() for b in bs.keys()]
        backups = {}
        for backup_id in backup_ids:
            backups[backup_id] = {}
            backups[backup_id]['machines'] = {}
            backups[backup_id]['info'] = []
            backups[backup_id]['status'] = 'complete'
            backup = backups[backup_id]
            for m in self.active.itervalues():
                if should_do(m, include, exclude):
                    if backup_id in machine_backups[m.name].keys():
                        backup['machines'][m.name] = machine_backups[m.name][backup_id]
                        backup['info'].extend(backup['machines'][m.name]['info'])
                        # status is always running when one of the backups is still running
                        if backup['machines'][m.name]['status'] != "complete" and backup['status'] != "running":
                            backup['status'] = backup['machines'][m.name]['status']
                    else:
                        backup['status'] = 'incomplete'
                        backup['info'].extend(["No backup available for {0}".format(m.name)]);

        return backups

    def clean_backups(self, keep=10):
        _backups = self.get_backups()
        backup_ids = [b for b in _backups.keys()]
        backup_ids.sort()
        index = len(backup_ids)-keep
        for backup_id in backup_ids[:index]:
            print 'Removing backup {0}'.format(backup_id)
            self.remove_backup(backup_id)

    def remove_backup(self, backup_id):
        with self._get_deployment_lock():
            def worker(m):
                m.remove_backup(backup_id)

            nixops.parallel.run_tasks(nr_workers=len(self.active), tasks=self.machines.itervalues(), worker_fun=worker)


    def backup(self, include=[], exclude=[]):
        self.evaluate_active(include, exclude) # unnecessary?
        backup_id = datetime.now().strftime("%Y%m%d%H%M%S");

        def worker(m):
            if not should_do(m, include, exclude): return
            ssh_name = m.get_ssh_name()
            res = subprocess.call(["ssh", "root@" + ssh_name] + m.get_ssh_flags() + ["sync"])
            if res != 0:
                m.logger.log("Running sync failed on {0}.".format(m.name))
            m.backup(self.definitions[m.name], backup_id)

        nixops.parallel.run_tasks(nr_workers=5, tasks=self.active.itervalues(), worker_fun=worker)

        return backup_id


    def restore(self, include=[], exclude=[], backup_id=None, devices=[]):
        with self._get_deployment_lock():

            self.evaluate_active(include, exclude)
            def worker(m):
                if not should_do(m, include, exclude): return
                m.restore(self.definitions[m.name], backup_id, devices)

            nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active.itervalues(), worker_fun=worker)
            self.start_machines(include=include, exclude=exclude)
            self.logger.warn("restore finished; please note that you might need to run ‘nixops deploy’ to fix configuration issues regarding changed IP addresses")


    def evaluate_active(self, include=[], exclude=[], kill_obsolete=False):
        self.evaluate()

        # Create state objects for all defined resources.
        with self._db:
            for m in self.definitions.itervalues():
                if m.name not in self.resources:
                    self._create_resource(m.name, m.get_type())

        self.logger.update_log_prefixes()

        # Determine the set of active resources.  (We can't just
        # delete obsolete resources from ‘self.resources’ because they
        # contain important state that we don't want to forget about.)
        for m in self.resources.values():
            if m.name in self.definitions:
                if m.obsolete:
                    self.logger.log("resource ‘{0}’ is no longer obsolete".format(m.name))
                    m.obsolete = False
            else:
                self.logger.log("resource ‘{0}’ is obsolete".format(m.name))
                if not m.obsolete: m.obsolete = True
                if not should_do(m, include, exclude): continue
                if kill_obsolete and m.destroy(): self.delete_resource(m)


    def _deploy(self, dry_run=False, build_only=False, create_only=False, copy_only=False,
                include=[], exclude=[], check=False, kill_obsolete=False,
                allow_reboot=False, allow_recreate=False, force_reboot=False,
                max_concurrent_copy=5, sync=True, always_activate=False, repair=False):
        """Perform the deployment defined by the deployment specification."""

        self.evaluate_active(include, exclude, kill_obsolete)

        # Assign each resource an index if it doesn't have one.
        for r in self.active_resources.itervalues():
            if r.index == None:
                r.index = self._get_free_resource_index()
                # FIXME: Logger should be able to do coloring without the need
                #        for an index maybe?
                r.logger.register_index(r.index)

        self.logger.update_log_prefixes()

        # Start or update the active resources.  Non-machine resources
        # are created first, because machines may depend on them
        # (e.g. EC2 machines depend on EC2 key pairs or EBS volumes).
        # FIXME: would be nice to have a more fine-grained topological
        # sort.
        if not dry_run and not build_only:

            for r in self.active_resources.itervalues():
                defn = self.definitions[r.name]
                if r.get_type() != defn.get_type():
                    raise Exception("the type of resource ‘{0}’ changed from ‘{1}’ to ‘{2}’, which is currently unsupported"
                                    .format(r.name, r.get_type(), defn.get_type()))
                r._created_event = threading.Event()
                r._errored = False

            def worker(r):
                try:
                    if not should_do(r, include, exclude): return

                    # Sleep until all dependencies of this resource have
                    # been created.
                    deps = r.create_after(self.active_resources.itervalues())
                    for dep in deps:
                        dep._created_event.wait()
                        # !!! Should we print a message here?
                        if dep._errored:
                            r._errored = True
                            return

                    # Now create the resource itself.
                    r.create(self.definitions[r.name], check=check, allow_reboot=allow_reboot, allow_recreate=allow_recreate)
                    if is_machine(r):
                        r.wait_for_ssh(check=check)
                        r.generate_vpn_key()
                except:
                    r._errored = True
                    raise
                finally:
                    r._created_event.set()

            nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active_resources.itervalues(), worker_fun=worker)

        if create_only: return

        # Build the machine configurations.
        if dry_run:
            self.build_configs(dry_run=True, repair=repair, include=include, exclude=exclude)
            return

        # Record configs_path in the state so that the ‘info’ command
        # can show whether machines have an outdated configuration.
        self.configs_path = self.build_configs(repair=repair, include=include, exclude=exclude)

        if build_only: return

        # Copy the closures of the machine configurations to the
        # target machines.
        self.copy_closures(self.configs_path, include=include, exclude=exclude,
                           max_concurrent_copy=max_concurrent_copy)

        if copy_only: return

        # Active the configurations.
        self.activate_configs(self.configs_path, include=include,
                              exclude=exclude, allow_reboot=allow_reboot,
                              force_reboot=force_reboot, check=check,
                              sync=sync, always_activate=always_activate)

        # Trigger cleanup of resources, e.g. disks that need to be detached etc. Needs to be
        # done after activation to make sure they are not in use anymore.
        def cleanup_worker(r):
            if not should_do(r, include, exclude): return

            # Now create the resource itself.
            r.after_activation(self.definitions[r.name])

        nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active_resources.itervalues(), worker_fun=cleanup_worker)


    def deploy(self, **kwargs):
        with self._get_deployment_lock():
            self._deploy(**kwargs)


    def _rollback(self, generation, include=[], exclude=[], check=False,
                  allow_reboot=False, force_reboot=False,
                  max_concurrent_copy=5, sync=True):
        if not self.rollback_enabled:
            raise Exception("rollback is not enabled for this network; please set ‘network.enableRollback’ to ‘true’ and redeploy"
                            )
        profile = self.get_profile()
        if subprocess.call(["nix-env", "-p", profile, "--switch-generation", str(generation)]) != 0:
            raise Exception("nix-env --switch-generation failed")

        self.configs_path = os.path.realpath(profile)
        assert os.path.isdir(self.configs_path)

        names = set()
        for filename in os.listdir(self.configs_path):
            if not os.path.islink(self.configs_path + "/" + filename): continue
            if should_do_n(filename, include, exclude) and filename not in self.machines:
                raise Exception("cannot roll back machine ‘{0}’ which no longer exists".format(filename))
            names.add(filename)

        # Update the set of active machines.
        for m in self.machines.values():
            if m.name in names:
                if m.obsolete:
                    self.logger.log("machine ‘{0}’ is no longer obsolete".format(m.name))
                    m.obsolete = False
            else:
                self.logger.log("machine ‘{0}’ is obsolete".format(m.name))
                if not m.obsolete: m.obsolete = True

        self.copy_closures(self.configs_path, include=include, exclude=exclude,
                           max_concurrent_copy=max_concurrent_copy)

        self.activate_configs(self.configs_path, include=include,
                              exclude=exclude, allow_reboot=allow_reboot,
                              force_reboot=force_reboot, check=check,
                              sync=sync, always_activate=True)


    def rollback(self, **kwargs):
        with self._get_deployment_lock():
            self._rollback(**kwargs)


    def destroy_resources(self, include=[], exclude=[], wipe=False):
        """Destroy all active or obsolete resources."""

        with self._get_deployment_lock():
            for r in self.resources.itervalues():
                r._destroyed_event = threading.Event()
                r._errored = False
                for rev_dep in r.destroy_before(self.resources.itervalues()):
                    try:
                        rev_dep._wait_for.append(r)
                    except AttributeError:
                        rev_dep._wait_for = [ r ]

            def worker(m):
                try:
                    if not should_do(m, include, exclude): return
                    try:
                        for dep in m._wait_for:
                            dep._destroyed_event.wait()
                            # !!! Should we print a message here?
                            if dep._errored:
                                m._errored = True
                                return
                    except AttributeError:
                        pass
                    if m.destroy(wipe=wipe): self.delete_resource(m)
                except:
                    m._errored = True
                    raise
                finally:
                    m._destroyed_event.set()

            nixops.parallel.run_tasks(nr_workers=-1, tasks=self.resources.values(), worker_fun=worker)

        # Remove the destroyed machines from the rollback profile.
        # This way, a subsequent "nix-env --delete-generations old" or
        # "nix-collect-garbage -d" will get rid of the machine
        # configurations.
        if self.rollback_enabled: # and len(self.active) == 0:
            profile = self.create_profile()
            attrs = {m.name:
                     Function("builtins.storePath", m.cur_toplevel, call=True)
                     for m in self.active.itervalues() if m.cur_toplevel}
            if subprocess.call(
                ["nix-env", "-p", profile, "--set", "*", "-I", "nixops=" + self.expr_path,
                 "-f", "<nixops/update-profile.nix>",
                 "--arg", "machines", py2nix(attrs, inline=True)]) != 0:
                raise Exception("cannot update profile ‘{0}’".format(profile))


    def reboot_machines(self, include=[], exclude=[], wait=False,
                        rescue=False, hard=False):
        """Reboot all active machines."""

        def worker(m):
            if not should_do(m, include, exclude): return
            if rescue:
                m.reboot_rescue(hard=hard)
            elif wait:
                m.reboot_sync(hard=hard)
            else:
                m.reboot(hard=hard)

        nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active.itervalues(), worker_fun=worker)


    def stop_machines(self, include=[], exclude=[]):
        """Stop all active machines."""

        def worker(m):
            if not should_do(m, include, exclude): return
            m.stop()

        nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active.itervalues(), worker_fun=worker)


    def start_machines(self, include=[], exclude=[]):
        """Start all active machines."""

        def worker(m):
            if not should_do(m, include, exclude): return
            m.start()

        nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active.itervalues(), worker_fun=worker)


    def is_valid_resource_name(self, name):
        p = re.compile('^[\w-]+$')
        return not p.match(name) is None


    def rename(self, name, new_name):
        if not name in self.resources:
            raise Exception("resource ‘{0}’ not found".format(name))
        if new_name in self.resources:
            raise Exception("resource with name ‘{0}’ already exists".format(new_name))
        if not self.is_valid_resource_name(new_name):
            raise Exception("{0} is not a valid resource identifier".format(new_name))

        self.logger.log("renaming resource ‘{0}’ to ‘{1}’...".format(name, new_name))

        m = self.resources.pop(name)
        self.resources[new_name] = m

        with self._db:
            self._db.execute("update Resources set name = ? where deployment = ? and id = ?", (new_name, self.uuid, m.id))


    def send_keys(self, include=[], exclude=[]):
        """Send LUKS encryption keys to machines."""

        def worker(m):
            if not should_do(m, include, exclude): return
            m.send_keys()

        nixops.parallel.run_tasks(nr_workers=-1, tasks=self.active.itervalues(), worker_fun=worker)


def should_do(m, include, exclude):
    return should_do_n(m.name, include, exclude)

def should_do_n(name, include, exclude):
    if name in exclude: return False
    if include == []: return True
    return name in include

def is_machine(r):
    return isinstance(r, nixops.backends.MachineState)

def is_machine_defn(r):
    return isinstance(r, nixops.backends.MachineDefinition)

########NEW FILE########
__FILENAME__ = ec2_utils
# -*- coding: utf-8 -*-

import os
import boto.ec2
import time
import random

from boto.exception import EC2ResponseError
from boto.exception import SQSError
from boto.exception import BotoServerError

def fetch_aws_secret_key(access_key_id):
    """Fetch the secret access key corresponding to the given access key ID from the environment or from ~/.ec2-keys"""
    secret_access_key = os.environ.get('EC2_SECRET_KEY') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    path = os.path.expanduser("~/.ec2-keys")
    if os.path.isfile(path):
        f = open(path, 'r')
        contents = f.read()
        f.close()
        for l in contents.splitlines():
            l = l.split("#")[0] # drop comments
            w = l.split()
            if len(w) < 2 or len(w) > 3: continue
            if len(w) == 3 and w[2] == access_key_id:
                access_key_id = w[0]
                secret_access_key = w[1]
                break
            if w[0] == access_key_id:
                secret_access_key = w[1]
                break

    if not secret_access_key:
        raise Exception("please set $EC2_SECRET_KEY or $AWS_SECRET_ACCESS_KEY, or add the key for ‘{0}’ to ~/.ec2-keys"
                        .format(access_key_id))

    return (access_key_id, secret_access_key)


def connect(region, access_key_id):
    """Connect to the specified EC2 region using the given access key."""
    assert region
    (access_key_id, secret_access_key) = fetch_aws_secret_key(access_key_id)
    conn = boto.ec2.connect_to_region(
        region_name=region, aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
    if not conn:
        raise Exception("invalid EC2 region ‘{0}’".format(region))
    return conn


def get_access_key_id():
    return os.environ.get('EC2_ACCESS_KEY') or os.environ.get('AWS_ACCESS_KEY_ID')


def retry(f, error_codes=[]):
    """
        Retry function f up to 7 times. If error_codes argument is empty list, retry on all EC2 response errors,
        otherwise, only on the specified error codes.
    """

    def handle_exception(e):
        if i == num_retries or (error_codes != [] and not e.error_code in error_codes):
            raise e

    i = 0
    num_retries = 7
    while i <= num_retries:
        i += 1
        next_sleep = 5 + random.random() * (2 ** i)

        try:
            return f()
        except EC2ResponseError as e:
            handle_exception(e)
        except SQSError as e:
            handle_exception(e)
        except BotoServerError as e:
            if e.error_code == "RequestLimitExceeded":
                num_retries += 1
            else:
                handle_exception(e)
        except Exception as e:
            raise e

        time.sleep(next_sleep)


def get_volume_by_id(conn, volume_id, allow_missing=False):
    """Get volume object by volume id."""
    try:
        volumes = conn.get_all_volumes([volume_id])
        if len(volumes) != 1:
            raise Exception("unable to find volume ‘{0}’".format(volume_id))
        return volumes[0]
    except boto.exception.EC2ResponseError as e:
        if e.error_code != "InvalidVolume.NotFound": raise
    return None

########NEW FILE########
__FILENAME__ = known_hosts
import os
import sys
import threading
import fcntl


# Allow only one thread to rewrite known_hosts at a time.
lock = threading.Lock()


def _rewrite(ip_address, public_host_key):
    with lock:
        path = os.path.expanduser("~/.ssh/known_hosts")
        if not os.path.isfile(path): return
    
        with open(os.path.expanduser("~/.ssh/.known_hosts.lock"), 'w') as lockfile:
            fcntl.flock(lockfile, fcntl.LOCK_EX) #unlock is implicit at the end of the with
            f = open(path, 'r')
            contents = f.read()
            f.close()

            def rewrite(l):
                (names, rest) = l.split(' ', 1)
                new_names = [ n for n in names.split(',') if n != ip_address ]
                return ','.join(new_names) + " " + rest if new_names != [] else None

            new = [ l for l in [ rewrite(l) for l in contents.splitlines() ] if l is not None ]

            if public_host_key:
                new.append(ip_address + " " + public_host_key)

            tmp = "{0}.tmp-{1}".format(path, os.getpid())
            f = open(tmp, 'w')
            f.write('\n'.join(new + [""]))
            f.close()
            os.rename(tmp, path)


def remove(ip_address):
    _rewrite(ip_address, None)


def add(ip_address, public_host_key):
    _rewrite(ip_address, public_host_key)

########NEW FILE########
__FILENAME__ = logger
# -*- coding: utf-8 -*-
import sys
import threading

from nixops.util import ansi_warn, ansi_success

__all__ = ['Logger']


class Logger(object):
    def __init__(self, log_file):
        self._last_log_prefix = None  # XXX!
        self._log_lock = threading.Lock()
        self._log_file = log_file
        self._auto_response = None
        self.machine_loggers = []

    @property
    def log_file(self):
        # XXX: Remove me soon!
        return self._log_file

    def isatty(self):
        return self._log_file.isatty()

    def log(self, msg):
        with self._log_lock:
            if self._last_log_prefix is not None:
                self._log_file.write("\n")
                self._last_log_prefix = None
            self._log_file.write(msg + "\n")

    def log_start(self, prefix, msg):
        with self._log_lock:
            if self._last_log_prefix != prefix:
                if self._last_log_prefix is not None:
                    self._log_file.write("\n")
                self._log_file.write(prefix)
            self._log_file.write(msg)
            self._last_log_prefix = prefix

    def log_end(self, prefix, msg):
        with self._log_lock:
            last = self._last_log_prefix
            self._last_log_prefix = None
            if last != prefix:
                if last is not None:
                    self._log_file.write("\n")
                if msg == "":
                    return
                self._log_file.write(prefix)
            self._log_file.write(msg + "\n")

    def get_logger_for(self, machine_name):
        """
        Returns a logger instance for a specific machine name.
        """
        machine_logger = MachineLogger(self, machine_name)
        self.machine_loggers.append(machine_logger)
        self.update_log_prefixes()
        return machine_logger

    def set_autoresponse(self, response):
        """
        Automatically respond to all confirmations with the response given by
        'response'.
        """
        self._auto_response = response

    def update_log_prefixes(self):
        max_len = max([len(ml.machine_name)
                       for ml in self.machine_loggers] or [0])
        for ml in self.machine_loggers:
            ml.update_log_prefix(max_len)

    def warn(self, msg):
        self.log(ansi_warn("warning: " + msg, outfile=self._log_file))

    def error(self, msg):
        self.log(ansi_warn("error: " + msg, outfile=self._log_file))

    def confirm_once(self, question):
        with self._log_lock:
            if self._last_log_prefix is not None:
                self._log_file.write("\n")
                self._last_log_prefix = None
            # XXX: This should be DRY!
            self._log_file.write(ansi_warn(
                "warning: {0} (y/N) ".format(question),
                outfile=self._log_file
            ))
            if self._auto_response is not None:
                self._log_file.write("{0}\n".format(self._auto_response))
                return self._auto_response == "y"
            response = sys.stdin.readline()
            if response == "":
                return False
            response = response.rstrip().lower()
            if response == "y":
                return True
            if response == "n" or response == "":
                return False
        return None

    def confirm(self, question):
        ret = None
        while ret is None:
            ret = self.confirm_once(question)
        return ret


class MachineLogger(object):
    def __init__(self, main_logger, machine_name):
        self.main_logger = main_logger
        self.machine_name = machine_name
        self.index = None
        self.update_log_prefix(0)

    def register_index(self, index):
        # FIXME Find a good way to do coloring based on machine name only.
        self.index = index

    def update_log_prefix(self, length):
        self._log_prefix = "{0}{1}> ".format(
            self.machine_name,
            '.' * (length - len(self.machine_name))
        )
        if self.main_logger.isatty() and self.index is not None:
            self._log_prefix = "\033[1;{0}m{1}\033[0m".format(
                31 + self.index % 7, self._log_prefix
            )

    def log(self, msg):
        self.main_logger.log(self._log_prefix + msg)

    def log_start(self, msg):
        self.main_logger.log_start(self._log_prefix, msg)

    def log_continue(self, msg):
        self.main_logger.log_start(self._log_prefix, msg)

    def log_end(self, msg):
        self.main_logger.log_end(self._log_prefix, msg)

    def warn(self, msg):
        self.log(ansi_warn("warning: " + msg,
                           outfile=self.main_logger._log_file))

    def error(self, msg):
        self.log(ansi_warn("error: " + msg,
                           outfile=self.main_logger._log_file))

    def success(self, msg):
        self.log(ansi_success(msg, outfile=self.main_logger._log_file))

########NEW FILE########
__FILENAME__ = nix_expr
import re
import string

from textwrap import dedent

__all__ = ['py2nix', 'nix2py', 'nixmerge', 'expand_dict',
           'RawValue', 'Function']


class RawValue(object):
    def __init__(self, value):
        self.value = value

    def get_min_length(self):
        return len(self.value)

    def is_inlineable(self):
        return True

    def indent(self, level=0, inline=False, maxwidth=80):
        return "  " * level + self.value

    def __repr__(self):
        return self.value

    def __eq__(self, other):
        return isinstance(other, RawValue) and other.value == self.value


class MultiLineRawValue(RawValue):
    def __init__(self, values):
        self.values = values

    def get_min_length(self):
        return None

    def is_inlineable(self):
        return False

    def indent(self, level=0, inline=False, maxwidth=80):
        return '\n'.join(["  " * level + value for value in self.values])


class Function(object):
    def __init__(self, head, body, call=False):
        self.head = head
        self.body = body
        self.call = call

    def __repr__(self):
        if self.call:
            return "{0}: {1}".format(self.head, self.body)
        else:
            return "{0} {1}".format(self.head, self.body)

    def __eq__(self, other):
        return (isinstance(other, Function)
                and other.head == self.head
                and other.body == self.body)


class Container(object):
    def __init__(self, prefix, children, suffix, inline_variant=None):
        self.prefix = prefix
        self.children = children
        self.suffix = suffix
        self.inline_variant = inline_variant

    def get_min_length(self):
        """
        Return the minimum length of this container and all sub-containers.
        """
        return (len(self.prefix) + len(self.suffix) + 1 + len(self.children) +
                sum([child.get_min_length() for child in self.children]))

    def is_inlineable(self):
        return all([child.is_inlineable() for child in self.children])

    def indent(self, level=0, inline=False, maxwidth=80):
        if not self.is_inlineable():
            inline = False
        elif level * 2 + self.get_min_length() < maxwidth:
            inline = True
        ind = "  " * level
        if inline and self.inline_variant is not None:
            return self.inline_variant.indent(level=level, inline=True,
                                              maxwidth=maxwidth)
        elif inline:
            sep = ' '
            lines = ' '.join([child.indent(level=0, inline=True)
                              for child in self.children])
            suffix_ind = ""
        else:
            sep = '\n'
            lines = '\n'.join([child.indent(level + 1, inline=inline,
                                            maxwidth=maxwidth)
                               for child in self.children])
            suffix_ind = ind
        return ind + self.prefix + sep + lines + sep + suffix_ind + self.suffix


def enclose_node(node, prefix="", suffix=""):
    if isinstance(node, MultiLineRawValue):
        new_values = list(node.values)
        new_values[0] = prefix + new_values[0]
        new_values[-1] += suffix
        return MultiLineRawValue(new_values)
    elif isinstance(node, RawValue):
        return RawValue(prefix + node.value + suffix)
    else:
        if node.inline_variant is not None:
            new_inline = RawValue(prefix + node.inline_variant.value + suffix)
        else:
            new_inline = None
        return Container(prefix + node.prefix, node.children,
                         node.suffix + suffix, new_inline)


def _fold_string(value, rules):
    folder = lambda val, rule: val.replace(rule[0], rule[1])
    return reduce(folder, rules, value)


def py2nix(value, initial_indentation=0, maxwidth=80, inline=False):
    """
    Return the given value as a Nix expression string.

    If initial_indentation is to a specific level (two spaces per level), don't
    inline fewer than that. Also, 'maxwidth' specifies the maximum line width
    which is enforced whenever it is possible to break an expression. Set to 0
    if you want to break on every occasion possible. If 'inline' is set to
    True, squash everything into a single line.
    """
    def _enc_int(node):
        if node < 0:
            return RawValue("builtins.sub 0 " + str(-node))
        else:
            return RawValue(str(node))

    def _enc_str(node, for_attribute=False):
        encoded = _fold_string(node, [
            ("\\", "\\\\"),
            ("${", "\\${"),
            ('"', '\\"'),
            ("\n", "\\n"),
            ("\t", "\\t"),
        ])

        inline_variant = RawValue('"{0}"'.format(encoded))

        if for_attribute:
            return inline_variant.value

        if node.endswith("\n"):
            encoded = _fold_string(node[:-1], [
                ("''", "'''"),
                ("${", "''${"),
                ("\t", "'\\t"),
            ])

            atoms = [RawValue(line) for line in encoded.splitlines()]
            return Container("''", atoms, "''", inline_variant=inline_variant)
        else:
            return inline_variant

    def _enc_list(nodes):
        if len(nodes) == 0:
            return RawValue("[]")
        pre, post = "[", "]"
        while len(nodes) == 1 and isinstance(nodes[0], list):
            nodes = nodes[0]
            pre, post = pre + " [", post + " ]"
        return Container(pre, map(lambda n: _enc(n, inlist=True), nodes), post)

    def _enc_key(key):
        if not isinstance(key, basestring):
            raise KeyError("key {0} is not a string".format(repr(key)))
        elif len(key) == 0:
            raise KeyError("key name has zero length")

        if all(char in string.letters + string.digits + '_'
               for char in key) and not key[0].isdigit():
            return key
        else:
            return _enc_str(key, for_attribute=True)

    def _enc_attrset(node):
        if len(node) == 0:
            return RawValue("{}")
        nodes = []
        for key, value in sorted(node.items()):
            encoded_key = _enc_key(key)

            # If the children are attrsets as well and only contain one
            # attribute, recursively merge them with a dot, like "a.b.c".
            child_key, child_value = key, value
            while isinstance(child_value, dict) and len(child_value) == 1:
                child_key, child_value = child_value.items()[0]
                encoded_key += "." + _enc_key(child_key)

            contents = _enc(child_value)
            prefix = "{0} = ".format(encoded_key)
            suffix = ";"

            nodes.append(enclose_node(contents, prefix, suffix))
        return Container("{", nodes, "}")

    def _enc_function(node):
        body = _enc(node.body)
        sep = " " if node.call else ": "
        return enclose_node(body, node.head + sep)

    def _enc(node, inlist=False):
        if isinstance(node, RawValue):
            if inlist and (isinstance(node, MultiLineRawValue) or
                           any(char.isspace() for char in node.value)):
                return enclose_node(node, "(", ")")
            else:
                return node
        elif node is True:
            return RawValue("true")
        elif node is False:
            return RawValue("false")
        elif node is None:
            return RawValue("null")
        elif isinstance(node, (int, long)):
            return _enc_int(node)
        elif isinstance(node, basestring):
            return _enc_str(node)
        elif isinstance(node, list):
            return _enc_list(node)
        elif isinstance(node, dict):
            return _enc_attrset(expand_dict(node))
        elif isinstance(node, Function):
            if inlist:
                return enclose_node(_enc_function(node), "(", ")")
            else:
                return _enc_function(node)
        else:
            raise ValueError("unable to encode {0}".format(repr(node)))

    return _enc(value).indent(initial_indentation, maxwidth=maxwidth,
                              inline=inline)


def expand_dict(unexpanded):
    """
    Turns a dict containing tuples as keys into a set of nested dictionaries.

    Examples:

    >>> expand_dict({('a', 'b', 'c'): 'd'})
    {'a': {'b': {'c': 'd'}}}
    >>> expand_dict({('a', 'b'): 'c',
    ...               'a': {('d', 'e'): 'f'}})
    {'a': {'b': 'c', 'd': {'e': 'f'}}}
    """
    paths, strings = [], {}
    for key, val in unexpanded.iteritems():
        if isinstance(key, tuple):
            if len(key) == 0:
                raise KeyError("invalid key {0}".format(repr(key)))

            newkey = key[0]
            if len(key) > 1:
                newval = {key[1:]: val}
            else:
                newval = val
            paths.append({newkey: newval})
        else:
            strings[key] = val

    return {key: (expand_dict(val) if isinstance(val, dict) else val)
            for key, val in reduce(nixmerge, paths + [strings]).iteritems()}


def nixmerge(expr1, expr2):
    """
    Merge both expressions into one, merging dictionary keys and appending list
    elements if they otherwise would clash.
    """
    def _merge_dicts(d1, d2):
        out = {}
        for key in set(d1.keys()).union(d2.keys()):
            if key in d1 and key in d2:
                out[key] = _merge(d1[key], d2[key])
            elif key in d1:
                out[key] = d1[key]
            else:
                out[key] = d2[key]
        return out

    def _merge(e1, e2):
        if isinstance(e1, dict) and isinstance(e2, dict):
            return _merge_dicts(e1, e2)
        elif isinstance(e1, list) and isinstance(e2, list):
            return list(set(e1).union(e2))
        else:
            err = "unable to merge {0} with {1}".format(type(e1), type(e2))
            raise ValueError(err)

    return _merge(expr1, expr2)


def nix2py(source):
    """
    Dedent the given Nix source code and encode it into multiple raw values
    which are used as-is and only indentation will take place.
    """
    return MultiLineRawValue(dedent(source).strip().splitlines())

########NEW FILE########
__FILENAME__ = parallel
import threading
import sys
import Queue
import random
import traceback

class MultipleExceptions(Exception):
    def __init__(self, exceptions=[]):
        self.exceptions = exceptions

    def __str__(self):
        return "Multiple exceptions: " + ", ".join([str(e[1]) for e in self.exceptions])

    def print_all_backtraces(self):
        for e in self.exceptions:
            sys.stderr.write('-'*30 + '\n')
            traceback.print_exception(e[0], e[1], e[2])


def run_tasks(nr_workers, tasks, worker_fun):
    task_queue = Queue.Queue()
    result_queue = Queue.Queue()

    nr_tasks = 0
    for t in tasks: task_queue.put(t); nr_tasks = nr_tasks + 1

    if nr_tasks == 0: return []

    if nr_workers == -1: nr_workers = nr_tasks
    if nr_workers < 1: raise Exception("number of worker threads must be at least 1")

    def thread_fun():
        n = 0
        while True:
            try:
                t = task_queue.get(False)
            except Queue.Empty:
                break
            n = n + 1
            try:
                result_queue.put((worker_fun(t), None))
            except Exception as e:
                result_queue.put((None, sys.exc_info()))
        #sys.stderr.write("thread {0} did {1} tasks\n".format(threading.current_thread(), n))

    threads = []
    for n in range(nr_workers):
        thr = threading.Thread(target=thread_fun)
        thr.daemon = True
        thr.start()
        threads.append(thr)

    results = []
    exceptions = []
    while len(results) < nr_tasks:
        try:
            # Use a timeout to allow keyboard interrupts to be
            # processed.  The actual timeout value doesn't matter.
            (res, excinfo) = result_queue.get(True, 1000)
        except Queue.Empty:
            continue
        if excinfo:
            exceptions.append(excinfo)
        results.append(res)

    for thr in threads:
        thr.join()

    if len(exceptions) == 1:
        excinfo = exceptions[0]
        raise excinfo[0], excinfo[1], excinfo[2]

    if len(exceptions) > 1:
        raise MultipleExceptions(exceptions)

    return results

########NEW FILE########
__FILENAME__ = ebs_volume
# -*- coding: utf-8 -*-

# Automatic provisioning of AWS EBS volumes.

import time
import boto.ec2
import nixops.util
import nixops.resources
import nixops.ec2_utils


class EBSVolumeDefinition(nixops.resources.ResourceDefinition):
    """Definition of an EBS volume."""

    @classmethod
    def get_type(cls):
        return "ebs-volume"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.volume_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.region = xml.find("attrs/attr[@name='region']/string").get("value")
        self.zone = xml.find("attrs/attr[@name='zone']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")
        self.size = int(xml.find("attrs/attr[@name='size']/int").get("value"))
        self.snapshot = xml.find("attrs/attr[@name='snapshot']/string").get("value")

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region)


class EBSVolumeState(nixops.resources.ResourceState):
    """State of an EBS volume."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    region = nixops.util.attr_property("ec2.region", None)
    zone = nixops.util.attr_property("ec2.zone", None)
    volume_id = nixops.util.attr_property("ec2.volumeId", None)
    size = nixops.util.attr_property("ec2.size", None, int)


    @classmethod
    def get_type(cls):
        return "ebs-volume"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def show_type(self):
        s = super(EBSVolumeState, self).show_type()
        if self.state == self.UP: s = "{0} [{1}]".format(s, self.zone)
        return s


    @property
    def resource_id(self):
        return self.volume_id


    def connect(self, region):
        if self._conn: return
        self._conn = nixops.ec2_utils.connect(region, self.access_key_id)


    def create(self, defn, check, allow_reboot, allow_recreate):

        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        if self.state == self.UP and (self.region != defn.region or self.zone != defn.zone):
            raise Exception("changing the region or availability zone of an EBS volume is not supported")

        if self.state == self.UP and (defn.size != 0 and self.size != defn.size):
            raise Exception("changing the size an EBS volume is currently not supported")

        if self.state != self.UP:

            self.connect(defn.region)

            if defn.size == 0 and defn.snapshot != "":
                snapshots = self._conn.get_all_snapshots(snapshot_ids=[defn.snapshot])
                assert len(snapshots) == 1
                defn.size = snapshots[0].volume_size

            if defn.snapshot:
                self.log("creating EBS volume of {0} GiB from snapshot ‘{1}’...".format(defn.size, defn.snapshot))
            else:
                self.log("creating EBS volume of {0} GiB...".format(defn.size))

            volume = self._conn.create_volume(zone=defn.zone, size=defn.size, snapshot=defn.snapshot)

            # FIXME: if we crash before the next step, we forget the
            # volume we just created.  Doesn't seem to be anything we
            # can do about this.

            with self.depl._db:
                self.state = self.UP
                self.region = defn.region
                self.zone = defn.zone
                self.size = defn.size
                self.volume_id = volume.id

            self.log("volume ID is ‘{0}’".format(volume.id))


    def destroy(self, wipe=False):
        if self.state == self.UP:
            self.connect(self.region)
            volume = nixops.ec2_utils.get_volume_by_id(self._conn, self.volume_id, allow_missing=True)
            if volume:
                if not self.depl.logger.confirm("are you sure you want to destroy EBS volume ‘{0}’?".format(self.name)): return False
                self.log("destroying EBS volume ‘{0}’...".format(self.volume_id))
                volume.delete()
        return True

########NEW FILE########
__FILENAME__ = ec2_keypair
# -*- coding: utf-8 -*-

# Automatic provisioning of EC2 key pairs.

import nixops.util
import nixops.resources
import nixops.ec2_utils


class EC2KeyPairDefinition(nixops.resources.ResourceDefinition):
    """Definition of an EC2 key pair."""

    @classmethod
    def get_type(cls):
        return "ec2-keypair"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.keypair_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.region = xml.find("attrs/attr[@name='region']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region)


class EC2KeyPairState(nixops.resources.ResourceState):
    """State of an EC2 key pair."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    keypair_name = nixops.util.attr_property("ec2.keyPairName", None)
    public_key = nixops.util.attr_property("publicKey", None)
    private_key = nixops.util.attr_property("privateKey", None)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    region = nixops.util.attr_property("ec2.region", None)


    @classmethod
    def get_type(cls):
        return "ec2-keypair"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def show_type(self):
        s = super(EC2KeyPairState, self).show_type()
        if self.region: s = "{0} [{1}]".format(s, self.region)
        return s


    @property
    def resource_id(self):
        return self.keypair_name


    def get_definition_prefix(self):
        return "resources.ec2KeyPairs."


    def connect(self):
        if self._conn: return
        self._conn = nixops.ec2_utils.connect(self.region, self.access_key_id)


    def create(self, defn, check, allow_reboot, allow_recreate):

        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        # Generate the key pair locally.
        if not self.public_key:
            (private, public) = nixops.util.create_key_pair(type="rsa")
            with self.depl._db:
                self.public_key = public
                self.private_key = private

        # Upload the public key to EC2.
        if check or self.state != self.UP:

            self.region = defn.region
            self.connect()

            # Sometimes EC2 DescribeKeypairs return empty list on invalid
            # identifiers, which results in a IndexError exception from within boto,
            # work around that until we figure out what is causing this.
            try:
                kp = self._conn.get_key_pair(defn.keypair_name)
            except IndexError as e:
                kp = None

            # Don't re-upload the key if it exists and we're just checking.
            if not kp or self.state != self.UP:
                if kp: self._conn.delete_key_pair(defn.keypair_name)
                self.log("uploading EC2 key pair ‘{0}’...".format(defn.keypair_name))
                self._conn.import_key_pair(defn.keypair_name, self.public_key)

            with self.depl._db:
                self.state = self.UP
                self.keypair_name = defn.keypair_name


    def destroy(self, wipe=False):
        if self.state == self.UP:
            self.log("deleting EC2 key pair ‘{0}’...".format(self.keypair_name))
            self.connect()
            self._conn.delete_key_pair(self.keypair_name)

        return True

########NEW FILE########
__FILENAME__ = ec2_security_group
# -*- coding: utf-8 -*-

# Automatic provisioning of EC2 security groups.

import boto.ec2.securitygroup
import nixops.resources
import nixops.util
import nixops.ec2_utils

class EC2SecurityGroupDefinition(nixops.resources.ResourceDefinition):
    """Definition of an EC2 security group."""

    @classmethod
    def get_type(cls):
        return "ec2-security-group"

    def __init__(self, xml):
        super(EC2SecurityGroupDefinition, self).__init__(xml)
        self.security_group_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.security_group_description = xml.find("attrs/attr[@name='description']/string").get("value")
        self.region = xml.find("attrs/attr[@name='region']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")
        self.security_group_rules = []
        for rule_xml in xml.findall("attrs/attr[@name='rules']/list/attrs"):
            ip_protocol = rule_xml.find("attr[@name='protocol']/string").get("value")
            if ip_protocol == "icmp":
                from_port = int(rule_xml.find("attr[@name='typeNumber']/int").get("value"))
                to_port = int(rule_xml.find("attr[@name='codeNumber']/int").get("value"))
            else:
                from_port = int(rule_xml.find("attr[@name='fromPort']/int").get("value"))
                to_port = int(rule_xml.find("attr[@name='toPort']/int").get("value"))
            cidr_ip_xml = rule_xml.find("attr[@name='sourceIp']/string")
            if not cidr_ip_xml is None:
                self.security_group_rules.append([ ip_protocol, from_port, to_port, cidr_ip_xml.get("value") ])
            else:
                group_name = rule_xml.find("attr[@name='sourceGroup']/attrs/attr[@name='groupName']/string").get("value")
                owner_id = rule_xml.find("attr[@name='sourceGroup']/attrs/attr[@name='ownerId']/string").get("value")
                self.security_group_rules.append([ ip_protocol, from_port, to_port, group_name, owner_id ])


    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region)

class EC2SecurityGroupState(nixops.resources.ResourceState):
    """State of an EC2 security group."""

    region = nixops.util.attr_property("ec2.region", None)
    security_group_id = nixops.util.attr_property("ec2.securityGroupId", None)
    security_group_name = nixops.util.attr_property("ec2.securityGroupName", None)
    security_group_description = nixops.util.attr_property("ec2.securityGroupDescription", None)
    security_group_rules = nixops.util.attr_property("ec2.securityGroupRules", [], 'json')
    old_security_groups = nixops.util.attr_property("ec2.oldSecurityGroups", [], 'json')
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)

    @classmethod
    def get_type(cls):
        return "ec2-security-group"

    def __init__(self, depl, name, id):
        super(EC2SecurityGroupState, self).__init__(depl, name, id)
        self._conn = None

    def show_type(self):
        s = super(EC2SecurityGroupState, self).show_type()
        if self.region: s = "{0} [{1}]".format(s, self.region)
        return s

    def prefix_definition(self, attr):
        return {('resources', 'ec2SecurityGroups'): attr}

    def get_physical_spec(self):
        return {'groupId': self.security_group_id}

    @property
    def resource_id(self):
        return self.security_group_name

    def create_after(self, resources):
        #!!! TODO: Handle dependencies between security groups
        return {}

    def _connect(self):
        if self._conn: return
        self._conn = nixops.ec2_utils.connect(self.region, self.access_key_id)

    def create(self, defn, check, allow_reboot, allow_recreate):
        # Name or region change means a completely new security group
        if self.security_group_name and (defn.security_group_name != self.security_group_name or defn.region != self.region):
            with self.depl._db:
                self.state = self.UNKNOWN
                self.old_security_groups = self.old_security_groups + [{'name': self.security_group_name, 'region': self.region}]

        with self.depl._db:
            self.region = defn.region
            self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
            self.security_group_name = defn.security_group_name
            self.security_group_description = defn.security_group_description

        grp = None
        if check:
            with self.depl._db:
                self._connect()

                try:
                    grp = self._conn.get_all_security_groups([ defn.security_group_name ])[0]
                    self.state = self.UP
                    self.security_group_id = grp.id
                    self.security_group_description = grp.description
                    rules = []
                    for rule in grp.rules:
                        for grant in rule.grants:
                            new_rule = [ rule.ip_protocol, int(rule.from_port), int(rule.to_port) ]
                            if grant.cidr_ip:
                                new_rule.append(grant.cidr_ip)
                            else:
                                new_rule.append(grant.groupName)
                                new_rule.append(grant.owner_id)
                            rules.append(new_rule)
                    self.security_group_rules = rules
                except boto.exception.EC2ResponseError as e:
                    if e.error_code == u'InvalidGroup.NotFound':
                        self.state = self.Missing
                    else:
                        raise

        new_rules = set()
        old_rules = set()
        for rule in self.security_group_rules:
            old_rules.add(tuple(rule))
        for rule in defn.security_group_rules:
            tupled_rule = tuple(rule)
            if not tupled_rule in old_rules:
                new_rules.add(tupled_rule)
            else:
                old_rules.remove(tupled_rule)

        if self.state == self.MISSING or self.state == self.UNKNOWN:
            self._connect()
            try:
                self.logger.log("creating EC2 security group ‘{0}’...".format(self.security_group_name))
                grp = self._conn.create_security_group(self.security_group_name, self.security_group_description)
                self.security_group_id = grp.id
            except boto.exception.EC2ResponseError as e:
                if self.state != self.UNKNOWN or e.error_code != u'InvalidGroup.Duplicate':
                    raise
            self.state = self.STARTING #ugh

        if new_rules:
            self.logger.log("adding new rules to EC2 security group ‘{0}’...".format(self.security_group_name))
            if grp is None:
                self._connect()
                grp = self._conn.get_all_security_groups([ self.security_group_name ])[0]
            for rule in new_rules:
                if len(rule) == 4:
                    grp.authorize(ip_protocol=rule[0], from_port=rule[1], to_port=rule[2], cidr_ip=rule[3])
                else:
                    src_group = boto.ec2.securitygroup.SecurityGroup(owner_id=rule[4], name=rule[3])
                    grp.authorize(ip_protocol=rule[0], from_port=rule[1], to_port=rule[2], src_group=src_group)

        if old_rules:
            self.logger.log("removing old rules from EC2 security group ‘{0}’...".format(self.security_group_name))
            if grp is None:
                self._connect()
                grp = self._conn.get_all_security_groups([ self.security_group_name ])[0]
            for rule in old_rules:
                if len(rule) == 4:
                    grp.revoke(ip_protocol=rule[0], from_port=rule[1], to_port=rule[2], cidr_ip=rule[3])
                else:
                    src_group = boto.ec2.securitygroup.SecurityGroup(owner_id=rule[4], name=rule[3])
                    grp.revoke(ip_protocol=rule[0], from_port=rule[1], to_port=rule[2], src_group=src_group)
        self.security_group_rules = defn.security_group_rules

        self.state = self.UP

    def after_activation(self, defn):
        region = self.region
        self._connect()
        conn = self._conn
        for group in self.old_security_groups:
            if group['region'] != region:
                region = group['region']
                conn = nixops.ec2_utils.connect(region, self.access_key_id)
            try:
                conn.delete_security_group(group['name'])
            except boto.exception.EC2ResponseError as e:
                if e.error_code != u'InvalidGroup.NotFound':
                    raise
        self.old_security_groups = []

    def destroy(self, wipe=False):
        if self.state == self.UP or self.state == self.STARTING:
            self.logger.log("deleting EC2 security group `{0}'...".format(self.security_group_name))
            self._connect()
            self._conn.delete_security_group(self.security_group_name)
            self.state = self.MISSING
        return True

########NEW FILE########
__FILENAME__ = elastic_ip
# -*- coding: utf-8 -*-

# Automatic provisioning of EC2 elastic IP addresses.

import time
import boto.ec2
import nixops.util
import nixops.resources
import nixops.ec2_utils


class ElasticIPDefinition(nixops.resources.ResourceDefinition):
    """Definition of an EC2 elastic IP address."""

    @classmethod
    def get_type(cls):
        return "elastic-ip"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.region = xml.find("attrs/attr[@name='region']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region)


class ElasticIPState(nixops.resources.ResourceState):
    """State of an EC2 elastic IP address."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    region = nixops.util.attr_property("ec2.region", None)
    public_ipv4 = nixops.util.attr_property("ec2.ipv4", None)


    @classmethod
    def get_type(cls):
        return "elastic-ip"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def show_type(self):
        s = super(ElasticIPState, self).show_type()
        if self.state == self.UP: s = "{0} [{1}]".format(s, self.region)
        return s


    @property
    def resource_id(self):
        return self.public_ipv4


    def connect(self, region):
        if self._conn: return
        self._conn = nixops.ec2_utils.connect(region, self.access_key_id)


    def create(self, defn, check, allow_reboot, allow_recreate):

        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        if self.state == self.UP and (self.region != defn.region):
            raise Exception("changing the region of an elastic IP address is not supported")

        if self.state != self.UP:

            self.connect(defn.region)

            self.log("creating elastic IP address (region ‘{0}’)...".format(defn.region))
            address = self._conn.allocate_address()

            # FIXME: if we crash before the next step, we forget the
            # address we just created.  Doesn't seem to be anything we
            # can do about this.

            with self.depl._db:
                self.state = self.UP
                self.region = defn.region
                self.public_ipv4 = address.public_ip

            self.log("IP address is {0}".format(self.public_ipv4))


    def destroy(self, wipe=False):
        if self.state == self.UP:
            self.connect(self.region)
            try:
                res = self._conn.get_all_addresses(addresses=[self.public_ipv4])
                assert len(res) <= 1
                if len(res) == 1:
                    self.log("releasing elastic IP address {0}...".format(self.public_ipv4))
                    res[0].delete()
            except boto.exception.EC2ResponseError as e:
                if e.error_code != "InvalidAddress.NotFound":
                    raise
        return True

########NEW FILE########
__FILENAME__ = iam_role
# -*- coding: utf-8 -*-

# Automatic provisioning of AWS IAM roles.

import time
import boto
import boto.iam
import nixops.util
import nixops.resources
import nixops.ec2_utils
from xml.etree import ElementTree
from pprint import pprint

class IAMRoleDefinition(nixops.resources.ResourceDefinition):
    """Definition of an IAM Role."""

    @classmethod
    def get_type(cls):
        return "iam-role"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.role_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")
        self.policy = xml.find("attrs/attr[@name='policy']/string").get("value")

    def show_type(self):
        return "{0}".format(self.get_type())


class IAMRoleState(nixops.resources.ResourceState):
    """State of an IAM Role."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    role_name = nixops.util.attr_property("ec2.roleName", None)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    policy = nixops.util.attr_property("ec2.policy", None)

    @classmethod
    def get_type(cls):
        return "iam-role"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def show_type(self):
        s = super(IAMRoleState, self).show_type()
        return s


    @property
    def resource_id(self):
        return self.role_name


    def get_definition_prefix(self):
        return "resources.iamRoles."


    def connect(self):
        if self._conn: return
        (access_key_id, secret_access_key) = nixops.ec2_utils.fetch_aws_secret_key(self.access_key_id)
        self._conn = boto.connect_iam(
            aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)


    def _destroy(self):
        if self.state != self.UP: return
        self.connect()

        try:
            ip = self._conn.get_instance_profile(self.role_name)
            try:
                self._conn.remove_role_from_instance_profile(self.role_name, self.role_name)
            except:
                self.log("Could not remove role from instance profile. Perhaps already gone.")

            try:
                self._conn.get_role_policy(self.role_name, self.role_name)
                self.log("Removing role policy")
                self._conn.delete_role_policy(self.role_name, self.role_name)
            except:
                self.log("Could not find role policy")

            try:
                self._conn.get_role(self.role_name)
                self.log("Removing role")
                self._conn.delete_role(self.role_name)
            except:
                self.log("Could not find role")

            self.log("Removing instance profile")
            self._conn.delete_instance_profile(self.role_name)

        except:
            self.log("Could not find instance profile")


        with self.depl._db:
            self.state = self.MISSING
            self.role_name = None
            self.access_key_id = None
            self.policy = None


    def create_after(self, resources):
        # IAM roles can refer to S3 buckets.
        return {r for r in resources if
                isinstance(r, nixops.resources.s3_bucket.S3BucketState)}


    def _get_instance_profile(self, name):
        try:
            return self._conn.get_instance_profile(name)
        except:
            return


    def _get_role_policy(self, name):
        try:
            return self._conn.get_role_policy(name, name)
        except:
            return


    def _get_role(self, name):
        try:
            return self._conn.get_role(name)
        except:
            return


    def create(self, defn, check, allow_reboot, allow_recreate):

        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        self.connect()

        ip = self._get_instance_profile(defn.role_name)
        rp = self._get_role_policy(defn.role_name)
        r = self._get_role(defn.role_name)

        if not r:
            self.log("creating IAM role ‘{0}’...".format(defn.role_name))
            role = self._conn.create_role(defn.role_name)

        if not ip:
            self.log("creating IAM instance profile ‘{0}’...".format(defn.role_name))
            self._conn.create_instance_profile(defn.role_name, '/')
            self._conn.add_role_to_instance_profile(defn.role_name, defn.role_name)

        if not check:
            self._conn.put_role_policy(defn.role_name, defn.role_name, defn.policy)

        with self.depl._db:
            self.state = self.UP
            self.role_name = defn.role_name
            self.policy = defn.policy


    def destroy(self, wipe=False):
        self._destroy()
        return True

########NEW FILE########
__FILENAME__ = s3_bucket
# -*- coding: utf-8 -*-

# Automatic provisioning of AWS S3 buckets.

import time
import boto.s3.connection
import nixops.util
import nixops.resources
import nixops.ec2_utils


class S3BucketDefinition(nixops.resources.ResourceDefinition):
    """Definition of an S3 bucket."""

    @classmethod
    def get_type(cls):
        return "s3-bucket"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.bucket_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.region = xml.find("attrs/attr[@name='region']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region)


class S3BucketState(nixops.resources.ResourceState):
    """State of an S3 bucket."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    bucket_name = nixops.util.attr_property("ec2.bucketName", None)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    region = nixops.util.attr_property("ec2.region", None)


    @classmethod
    def get_type(cls):
        return "s3-bucket"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def show_type(self):
        s = super(S3BucketState, self).show_type()
        if self.region: s = "{0} [{1}]".format(s, self.region)
        return s


    @property
    def resource_id(self):
        return self.bucket_name

    def get_definition_prefix(self):
        return "resources.s3Buckets."

    def connect(self):
        if self._conn: return
        (access_key_id, secret_access_key) = nixops.ec2_utils.fetch_aws_secret_key(self.access_key_id)
        self._conn = boto.s3.connection.S3Connection(aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)


    def create(self, defn, check, allow_reboot, allow_recreate):

        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        if check or self.state != self.UP:

            self.connect()

            self.log("creating S3 bucket ‘{0}’...".format(defn.bucket_name))
            try:
                self._conn.create_bucket(defn.bucket_name, location=region_to_s3_location(defn.region))
            except boto.exception.S3CreateError as e:
                if e.error_code != "BucketAlreadyOwnedByYou": raise

            with self.depl._db:
                self.state = self.UP
                self.bucket_name = defn.bucket_name
                self.region = defn.region


    def destroy(self, wipe=False):
        if self.state == self.UP:
            self.connect()
            try:
                self.log("destroying S3 bucket ‘{0}’...".format(self.bucket_name))
                bucket = self._conn.get_bucket(self.bucket_name)
                try:
                    bucket.delete()
                except boto.exception.S3ResponseError as e:
                    if e.error_code != "BucketNotEmpty": raise
                    if not self.depl.logger.confirm("are you sure you want to destroy S3 bucket ‘{0}’?".format(self.bucket_name)): return False
                    keys = bucket.list()
                    bucket.delete_keys(keys)
                    bucket.delete()
            except boto.exception.S3ResponseError as e:
                if e.error_code != "NoSuchBucket": raise
        return True


def region_to_s3_location(region):
    # S3 location names are identical to EC2 regions, except for
    # us-east-1 and eu-west-1.
    if region == "eu-west-1": return "EU"
    elif region == "us-east-1": return ""
    else: return region

########NEW FILE########
__FILENAME__ = sqs_queue
# -*- coding: utf-8 -*-

# Automatic provisioning of AWS SQS queues.

import time
import boto.sqs
import nixops.util
import nixops.resources
import nixops.ec2_utils


class SQSQueueDefinition(nixops.resources.ResourceDefinition):
    """Definition of an SQS queue."""

    @classmethod
    def get_type(cls):
        return "sqs-queue"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.queue_name = xml.find("attrs/attr[@name='name']/string").get("value")
        self.region = xml.find("attrs/attr[@name='region']/string").get("value")
        self.access_key_id = xml.find("attrs/attr[@name='accessKeyId']/string").get("value")
        self.visibility_timeout = xml.find("attrs/attr[@name='visibilityTimeout']/int").get("value")

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.region)


class SQSQueueState(nixops.resources.ResourceState):
    """State of an SQS queue."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    queue_name = nixops.util.attr_property("ec2.queueName", None)
    access_key_id = nixops.util.attr_property("ec2.accessKeyId", None)
    region = nixops.util.attr_property("ec2.region", None)
    visibility_timeout = nixops.util.attr_property("ec2.queueVisibilityTimeout", None)
    url = nixops.util.attr_property("ec2.queueURL", None)
    arn = nixops.util.attr_property("ec2.queueARN", None)

    @classmethod
    def get_type(cls):
        return "sqs-queue"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def show_type(self):
        s = super(SQSQueueState, self).show_type()
        if self.region: s = "{0} [{1}]".format(s, self.region)
        return s

    def prefix_definition(self, attr):
        return {('resources', 'sqsQueues'): attr}

    def get_physical_spec(self):
        return {'url': self.url,
                'arn': self.arn}

    @property
    def resource_id(self):
        return self.queue_name


    def connect(self):
        if self._conn: return
        assert self.region
        (access_key_id, secret_access_key) = nixops.ec2_utils.fetch_aws_secret_key(self.access_key_id)
        self._conn = boto.sqs.connect_to_region(
            region_name=self.region, aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)


    def _destroy(self):
        if self.state != self.UP: return
        self.connect()
        q = self._conn.lookup(self.queue_name)
        if q:
            self.log("destroying SQS queue ‘{0}’...".format(self.queue_name))
            self._conn.delete_queue(q)
        with self.depl._db:
            self.state = self.MISSING
            self.queue_name = None
            self.queue_base_name = None
            self.url = None
            self.arn = None
            self.region = None
            self.access_key_id = None


    def create(self, defn, check, allow_reboot, allow_recreate):

        self.access_key_id = defn.access_key_id or nixops.ec2_utils.get_access_key_id()
        if not self.access_key_id:
            raise Exception("please set ‘accessKeyId’, $EC2_ACCESS_KEY or $AWS_ACCESS_KEY_ID")

        if self.state == self.UP and (self.queue_name != defn.queue_name or self.region != defn.region):
            self.log("queue definition changed, recreating...")
            self._destroy()
            self._conn = None # necessary if region changed

        if check or self.state != self.UP:

            self.region = defn.region
            self.connect()

            q = self._conn.lookup(defn.queue_name)

            if not q or self.state != self.UP:
                if q:
                    # SQS requires us to wait for 60 seconds to
                    # recreate a queue.
                    self.log("deleting queue ‘{0}’ (and waiting 60 seconds)...".format(defn.queue_name))
                    self._conn.delete_queue(q)
                    time.sleep(61)
                self.log("creating SQS queue ‘{0}’...".format(defn.queue_name))
                q = nixops.ec2_utils.retry(lambda: self._conn.create_queue(defn.queue_name, defn.visibility_timeout), error_codes = ['AWS.SimpleQueueService.QueueDeletedRecently'])

            with self.depl._db:
                self.state = self.UP
                self.queue_name = defn.queue_name
                self.url = q.url
                self.arn = q.get_attributes()['QueueArn']

    def destroy(self, wipe=False):
        self._destroy()
        return True

########NEW FILE########
__FILENAME__ = ssh_keypair
# -*- coding: utf-8 -*-

# Automatic provisioning of SSH key pairs.

import nixops.util
import nixops.resources


class SSHKeyPairDefinition(nixops.resources.ResourceDefinition):
    """Definition of an SSH key pair."""

    @classmethod
    def get_type(cls):
        return "ssh-keypair"

    def __init__(self, xml):
        nixops.resources.ResourceDefinition.__init__(self, xml)

    def show_type(self):
        return "{0}".format(self.get_type())


class SSHKeyPairState(nixops.resources.ResourceState):
    """State of an SSH key pair."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    public_key = nixops.util.attr_property("publicKey", None)
    private_key = nixops.util.attr_property("privateKey", None)


    @classmethod
    def get_type(cls):
        return "ssh-keypair"


    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._conn = None


    def create(self, defn, check, allow_reboot, allow_recreate):
        # Generate the key pair locally.
        if not self.public_key:
            (private, public) = nixops.util.create_key_pair(type="rsa")
            with self.depl._db:
                self.public_key = public
                self.private_key = private
                self.state = state = nixops.resources.ResourceState.UP

    def prefix_definition(self, attr):
        return {('resources', 'sshKeyPairs'): attr}

    def get_physical_spec(self):
        return {'privateKey': self.private_key,
                'publicKey': self.public_key}

    def destroy(self, wipe=False):
        return True

########NEW FILE########
__FILENAME__ = ssh_util
# -*- coding: utf-8 -*-
import os
import shlex
import subprocess
import weakref

from tempfile import mkdtemp

import nixops.util

__all__ = ['SSHConnectionFailed', 'SSHCommandFailed', 'SSH']


class SSHConnectionFailed(Exception):
    pass


class SSHCommandFailed(nixops.util.CommandFailed):
    pass


class SSHMaster(object):
    def __init__(self, target, logger, ssh_flags, passwd):
        self._tempdir = mkdtemp(prefix="nixops-tmp")
        self._askpass_helper = None
        self._control_socket = self._tempdir + "/ssh-master-socket"
        self._ssh_target = target
        pass_prompts = 0
        kwargs = {}
        additional_opts = []
        if passwd is not None:
            self._askpass_helper = self._make_askpass_helper()
            newenv = dict(os.environ)
            newenv.update({
                'DISPLAY': ':666',
                'SSH_ASKPASS': self._askpass_helper,
                'NIXOPS_SSH_PASSWORD': passwd,
            })
            kwargs['env'] = newenv
            kwargs['stdin'] = nixops.util.devnull
            kwargs['preexec_fn'] = os.setsid
            pass_prompts = 1
            additional_opts = ['-oUserKnownHostsFile=/dev/null',
                               '-oStrictHostKeyChecking=no']
        cmd = ["ssh", "-x", self._ssh_target, "-S",
               self._control_socket, "-M", "-N", "-f",
               '-oNumberOfPasswordPrompts={0}'.format(pass_prompts),
               '-oServerAliveInterval=60'] + additional_opts
        res = subprocess.call(cmd + ssh_flags, **kwargs)
        if res != 0:
            raise SSHConnectionFailed(
                "unable to start SSH master connection to "
                "‘{0}’".format(logger.machine_name)
            )
        self.opts = ["-oControlPath={0}".format(self._control_socket)]

    def _make_askpass_helper(self):
        """
        Create a SSH_ASKPASS helper script, which just outputs the contents of
        the environment variable NIXOPS_SSH_PASSWORD.
        """
        path = os.path.join(self._tempdir, 'nixops-askpass-helper')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0700)
        os.write(fd, "#!{0}\necho -n \"$NIXOPS_SSH_PASSWORD\"".format(
            nixops.util.which("sh")
        ))
        os.close(fd)
        return path

    def shutdown(self):
        """
        Shutdown master process and clean up temporary files.
        """
        subprocess.call(["ssh", self._ssh_target, "-S",
                         self._control_socket, "-O", "exit"],
                        stderr=nixops.util.devnull)
        for to_unlink in (self._askpass_helper, self._control_socket):
            if to_unlink is None:
                continue
            try:
                os.unlink(to_unlink)
            except OSError:
                pass
        try:
            os.rmdir(self._tempdir)
        except OSError:
            pass

    def __del__(self):
        self.shutdown()


class SSH(object):
    def __init__(self, logger):
        """
        Initialize a SSH object with the specified Logger instance, which will
        be used to write SSH output to.
        """
        self._flag_fun = lambda: []
        self._host_fun = None
        self._passwd_fun = lambda: None
        self._logger = logger
        self._ssh_master = None

    def register_host_fun(self, host_fun):
        """
        Register a function which returns the hostname or IP to connect to. The
        function has to require no arguments.
        """
        self._host_fun = host_fun

    def _get_target(self):
        if self._host_fun is None:
            raise AssertionError("Don't know which SSH host to connect to.")
        return "root@{0}".format(self._host_fun())

    def register_flag_fun(self, flag_fun):
        """
        Register a function that is used for obtaining additional SSH flags.
        The function has to require no arguments and should return a list of
        strings, each being a SSH flag/argument.
        """
        self._flag_fun = flag_fun

    def _get_flags(self):
        return self._flag_fun()

    def register_passwd_fun(self, passwd_fun):
        """
        Register a function that returns either a string or None and requires
        no arguments. If the return value is a string, the returned string is
        used for keyboard-interactive authentication, if it is None, no attempt
        is made to inject a password.
        """
        self._passwd_fun = passwd_fun

    def _get_passwd(self):
        return self._passwd_fun()

    def reset(self):
        """
        Reset SSH master connection.
        """
        if self._ssh_master is not None:
            self._ssh_master.shutdown()
            self._ssh_master = None

    def get_master(self, flags=[], tries=5):
        """
        Start (if necessary) an SSH master connection to speed up subsequent
        SSH sessions. Returns the SSHMaster instance on success.
        """
        flags = flags + self._get_flags()
        if self._ssh_master is not None:
            return weakref.proxy(self._ssh_master)

        while True:
            try:
                self._ssh_master = SSHMaster(self._get_target(), self._logger,
                                             flags, self._get_passwd())
                break
            except Exception:
                tries = tries - 1
                if tries == 0:
                    raise
                pass
        return weakref.proxy(self._ssh_master)

    def _sanitize_command(self, command, allow_ssh_args):
        """
        Helper method for run_command, which essentially prepares and properly
        escape the command. See run_command() for further description.
        """
        if isinstance(command, basestring):
            if allow_ssh_args:
                return shlex.split(command)
            else:
                return ['--', command]
        # iterable
        elif allow_ssh_args:
            return command
        else:
            return ['--', ' '.join(["'{0}'".format(arg.replace("'", r"'\''"))
                                    for arg in command])]

    def run_command(self, command, flags=[], timeout=None, logged=True,
                    allow_ssh_args=False, **kwargs):
        """
        Execute a 'command' on the current target host using SSH, passing
        'flags' as additional arguments to SSH. The command can be either a
        string or an iterable of strings, whereby if it's the latter, it will
        be joined with spaces and properly shell-escaped.

        If 'allow_ssh_args' is set to True, the specified command may contain
        SSH flags.

        All keyword arguments except timeout are passed as-is to
        nixops.util.logged_exec(), though if you set 'logged' to False, the
        keyword arguments are passed as-is to subprocess.call() and the command
        is executed interactively with no logging.

        'timeout' specifies the SSH connection timeout.
        """
        tries = 5
        if timeout is not None:
            flags = flags + ["-o", "ConnectTimeout={0}".format(timeout)]
            tries = 1
        master = self.get_master(flags, tries)
        flags = flags + self._get_flags()
        if logged:
            flags.append("-x")
        cmd = ["ssh"] + master.opts + flags
        cmd.append(self._get_target())
        cmd += self._sanitize_command(command, allow_ssh_args)
        if logged:
            try:
                return nixops.util.logged_exec(cmd, self._logger, **kwargs)
            except nixops.util.CommandFailed as exc:
                raise SSHCommandFailed(exc.message, exc.exitcode)
        else:
            check = kwargs.pop('check', True)
            res = subprocess.call(cmd, **kwargs)
            if check and res != 0:
                msg = "command ‘{0}’ failed on host ‘{1}’"
                err = msg.format(cmd, self._get_target())
                raise SSHCommandFailed(err, res)
            else:
                return res

########NEW FILE########
__FILENAME__ = statefile
# -*- coding: utf-8 -*-

import nixops.deployment
import os
import os.path
import sqlite3
import sys
import threading


class Connection(sqlite3.Connection):

    def __init__(self, db_file, **kwargs):
        sqlite3.Connection.__init__(self, db_file, **kwargs)
        self.db_file = db_file
        self.nesting = 0
        self.lock = threading.RLock()

    # Implement Python's context management protocol so that "with db"
    # automatically commits or rolls back.  The difference with the
    # parent's "with" implementation is that we nest, i.e. a commit or
    # rollback is only done at the outer "with".
    def __enter__(self):
        self.lock.acquire()
        if self.nesting == 0:
            self.must_rollback = False
        self.nesting = self.nesting + 1

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if exception_type != None: self.must_rollback = True
        self.nesting = self.nesting - 1
        assert self.nesting >= 0
        if self.nesting == 0:
            if self.must_rollback:
                try:
                    self.rollback()
                except sqlite3.ProgrammingError:
                    pass
            else:
                self.commit()
        self.lock.release()


def get_default_state_file():
    home = os.environ.get("HOME", "") + "/.nixops"
    if not os.path.exists(home):
        old_home = os.environ.get("HOME", "") + "/.charon"
        if os.path.exists(old_home):
            sys.stderr.write("renaming ‘{0}’ to ‘{1}’...\n".format(old_home, home))
            os.rename(old_home, home)
            if os.path.exists(home + "/deployments.charon"):
                os.rename(home + "/deployments.charon", home + "/deployments.nixops")
        else:
            os.makedirs(home, 0700)
    return os.environ.get("NIXOPS_STATE", os.environ.get("CHARON_STATE", home + "/deployments.nixops"))


class StateFile(object):
    """NixOps state file."""

    current_schema = 3

    def __init__(self, db_file):
        self.db_file = db_file

        if os.path.splitext(db_file)[1] not in ['.nixops', '.charon']:
            raise Exception("state file ‘{0}’ should have extension ‘.nixops’".format(db_file))
        db = sqlite3.connect(db_file, timeout=60, check_same_thread=False, factory=Connection) # FIXME
        db.db_file = db_file

        db.execute("pragma journal_mode = wal")
        db.execute("pragma foreign_keys = 1")

        # FIXME: this is not actually transactional, because pysqlite (not
        # sqlite) does an implicit commit before "create table".
        with db:
            c = db.cursor()

            # Get the schema version.
            version = 0 # new database
            if self._table_exists(c, 'SchemaVersion'):
                c.execute("select version from SchemaVersion")
                version = c.fetchone()[0]
            elif self._table_exists(c, 'Deployments'):
                version = 1

            if version == self.current_schema:
                pass
            elif version == 0:
                self._create_schema(c)
            elif version < self.current_schema:
                if version <= 1: self._upgrade_1_to_2(c)
                if version <= 2: self._upgrade_2_to_3(c)
                c.execute("update SchemaVersion set version = ?", (self.current_schema,))
            else:
                raise Exception("this NixOps version is too old to deal with schema version {0}".format(version))

        self._db = db

    def close(self):
        self._db.close()

    def query_deployments(self):
        """Return the UUIDs of all deployments in the database."""
        c = self._db.cursor()
        c.execute("select uuid from Deployments")
        res = c.fetchall()
        return [x[0] for x in res]

    def get_all_deployments(self):
        """Return Deployment objects for every deployment in the database."""
        uuids = self.query_deployments()
        res = []
        for uuid in uuids:
            try:
                res.append(self.open_deployment(uuid=uuid))
            except nixops.deployment.UnknownBackend as e:
                sys.stderr.write("skipping deployment ‘{0}’: {1}\n".format(uuid, str(e)))
        return res

    def _find_deployment(self, uuid=None):
        c = self._db.cursor()
        if not uuid:
            c.execute("select uuid from Deployments")
        else:
            c.execute("select uuid from Deployments d where uuid = ? or exists (select 1 from DeploymentAttrs where deployment = d.uuid and name = 'name' and value = ?)", (uuid, uuid))
        res = c.fetchall()
        if len(res) == 0:
            if uuid:
                # try the prefix match
                c.execute("select uuid from Deployments where uuid glob ?", (uuid + '*', ))
                res = c.fetchall()
                if len(res) == 0:
                    return None
            else:
                return None
        if len(res) > 1:
            if uuid:
                raise Exception("state file contains multiple deployments with the same name, so you should specify one using its UUID")
            else:
                raise Exception("state file contains multiple deployments, so you should specify which one to use using ‘-d’, or set the environment variable NIXOPS_DEPLOYMENT")
        return nixops.deployment.Deployment(self, res[0][0], sys.stderr)

    def open_deployment(self, uuid=None):
        """Open an existing deployment."""
        deployment = self._find_deployment(uuid=uuid)
        if deployment: return deployment
        raise Exception("could not find specified deployment in state file ‘{0}’".format(self.db_file))

    def create_deployment(self, uuid=None):
        """Create a new deployment."""
        if not uuid:
            import uuid
            uuid = str(uuid.uuid1())
        with self._db:
            self._db.execute("insert into Deployments(uuid) values (?)", (uuid,))
        return nixops.deployment.Deployment(self, uuid, sys.stderr)

    def _table_exists(self, c, table):
        c.execute("select 1 from sqlite_master where name = ? and type='table'", (table,));
        return c.fetchone() != None

    def _create_schemaversion(self, c):
        c.execute(
            '''create table if not exists SchemaVersion(
                 version integer not null
               );''')

        c.execute("insert into SchemaVersion(version) values (?)", (self.current_schema,))

    def _create_schema(self, c):
        self._create_schemaversion(c)

        c.execute(
            '''create table if not exists Deployments(
                 uuid text primary key
               );''')

        c.execute(
            '''create table if not exists DeploymentAttrs(
                 deployment text not null,
                 name text not null,
                 value text not null,
                 primary key(deployment, name),
                 foreign key(deployment) references Deployments(uuid) on delete cascade
               );''')

        c.execute(
            '''create table if not exists Resources(
                 id integer primary key autoincrement,
                 deployment text not null,
                 name text not null,
                 type text not null,
                 foreign key(deployment) references Deployments(uuid) on delete cascade
               );''')

        c.execute(
            '''create table if not exists ResourceAttrs(
                 machine integer not null,
                 name text not null,
                 value text not null,
                 primary key(machine, name),
                 foreign key(machine) references Resources(id) on delete cascade
               );''')

    def _upgrade_1_to_2(self, c):
        sys.stderr.write("updating database schema from version 1 to 2...\n")
        self._create_schemaversion(c)

    def _upgrade_2_to_3(self, c):
        sys.stderr.write("updating database schema from version 2 to 3...\n")
        c.execute("alter table Machines rename to Resources")
        c.execute("alter table MachineAttrs rename to ResourceAttrs")



########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import copy
import fcntl
import base64
import select
import socket
import struct
import shutil
import tempfile
import subprocess
import logging
from StringIO import StringIO

devnull = open(os.devnull, 'rw')


def check_wait(test, initial=10, factor=1, max_tries=60, exception=True):
    """Call function ‘test’ periodically until it returns True or a timeout occurs."""
    wait = initial
    tries = 0
    while tries < max_tries and not test():
        time.sleep(wait)
        wait = wait * factor
        tries = tries + 1
        if tries == max_tries:
            if exception: raise Exception("operation timed out")
            return False
    return True


class CommandFailed(Exception):
    def __init__(self, message, exitcode):
        self.message = message
        self.exitcode = exitcode

    def __str__(self):
        return "{0} (exit code {1}".format(self.message, self.exitcode)


def logged_exec(command, logger, check=True, capture_stdout=False, stdin=None,
                stdin_string=None, env=None):
    """
    Execute a command with logging using the specified logger.

    The command itself has to be an iterable of strings, just like
    subprocess.Popen without shell=True. Keywords stdin and env have the same
    functionality as well.

    When calling with capture_stdout=True, a string is returned, which contains
    everything the programm wrote to stdout.

    When calling with check=False, the return code isn't checked and the
    function will return an integer which represents the return code of the
    program, otherwise a CommandFailed exception is thrown.
    """
    if stdin_string is not None:
        stdin = subprocess.PIPE
    elif stdin is None:
        stdin = devnull

    if capture_stdout:
        process = subprocess.Popen(command, env=env, stdin=stdin,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        fds = [process.stdout, process.stderr]
        log_fd = process.stderr
    else:
        process = subprocess.Popen(command, env=env, stdin=stdin,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        fds = [process.stdout]
        log_fd = process.stdout

    # FIXME: this can deadlock if stdin_string doesn't fit in the
    # kernel pipe buffer.
    if stdin_string is not None:
        process.stdin.write(stdin_string)
        process.stdin.close()

    for fd in fds:
        make_non_blocking(fd)

    at_new_line = True
    stdout = ""

    while len(fds) > 0:
        # The timeout/poll is to deal with processes (like
        # VBoxManage) that start children that go into the
        # background but keep the parent's stdout/stderr open,
        # preventing an EOF.  FIXME: Would be better to catch
        # SIGCHLD.
        (r, w, x) = select.select(fds, [], [], 1)
        if len(r) == 0 and process.poll() is not None:
            break
        if capture_stdout and process.stdout in r:
            data = process.stdout.read()
            if data == "":
                fds.remove(process.stdout)
            else:
                stdout += data
        if log_fd in r:
            data = log_fd.read()
            if data == "":
                if not at_new_line:
                    logger.log_end("")
                fds.remove(log_fd)
            else:
                start = 0
                while start < len(data):
                    end = data.find('\n', start)
                    if end == -1:
                        logger.log_start(data[start:])
                        at_new_line = False
                    else:
                        s = data[start:end]
                        if at_new_line:
                            logger.log(s)
                        else:
                            logger.log_end(s)
                        at_new_line = True
                    if end == -1:
                        break
                    start = end + 1

    res = process.wait()

    if check and res != 0:
        msg = "command ‘{0}’ failed on machine ‘{1}’"
        err = msg.format(command, logger.machine_name)
        raise CommandFailed(err, res)
    return stdout if capture_stdout else res


def generate_random_string(length=256):
    """Generate a base-64 encoded cryptographically strong random string."""
    s = os.urandom(length)
    assert len(s) == length
    return base64.b64encode(s)


def make_non_blocking(fd):
    fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)


def ping_tcp_port(ip, port, timeout=1, ensure_timeout=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    try:
        s.connect((ip, port))
    except socket.timeout:
        return False
    except:
        # FIXME: check that we got a transient error (like connection
        # refused or no route to host). For any other error, throw an
        # exception.
        if ensure_timeout: time.sleep(timeout)
        return False
    s.shutdown(socket.SHUT_RDWR)
    return True


def wait_for_tcp_port(ip, port, timeout=-1, open=True, callback=None):
    """Wait until the specified TCP port is open or closed."""
    n = 0
    while True:
        if ping_tcp_port(ip, port, ensure_timeout=True) == open: return True
        if not open: time.sleep(1)
        n = n + 1
        if timeout != -1 and n >= timeout: break
        if callback: callback()
    raise Exception("timed out waiting for port {0} on ‘{1}’".format(port, ip))


def ansi_highlight(s, outfile=sys.stderr):
    return "\033[1;33m" + s + "\033[0m" if outfile.isatty() else s


def ansi_warn(s, outfile=sys.stderr):
    return "\033[1;31m" + s + "\033[0m" if outfile.isatty() else s


def ansi_success(s, outfile=sys.stderr):
    return "\033[1;32m" + s + "\033[0m" if outfile.isatty() else s


def abs_nix_path(x):
    xs = x.split('=', 1)
    if len(xs) == 1: return os.path.abspath(x)
    return xs[0] + '=' + os.path.abspath(xs[1])


undefined = object()

def attr_property(name, default, type=str):
    """Define a property that corresponds to a value in the NixOps state file."""
    def get(self):
        s = self._get_attr(name, default)
        if s == undefined:
            if default != undefined: return copy.deepcopy(default)
            raise Exception("deployment attribute ‘{0}’ missing from state file".format(name))
        if s == None: return None
        elif type is str: return s
        elif type is int: return int(s)
        elif type is bool: return True if s == "1" else False
        elif type is 'json': return json.loads(s)
        else: assert False
    def set(self, x):
        if x == default: self._del_attr(name)
        elif type is 'json': self._set_attr(name, json.dumps(x))
        else: self._set_attr(name, x)
    return property(get, set)


def create_key_pair(key_name="NixOps auto-generated key", type="ecdsa"):
    key_dir = tempfile.mkdtemp(prefix="nixops-tmp")
    res = subprocess.call(["ssh-keygen", "-t", type, "-f", key_dir + "/key", "-N", '', "-C", key_name],
                          stdout=devnull)
    if res != 0: raise Exception("unable to generate an SSH key")
    f = open(key_dir + "/key"); private = f.read(); f.close()
    f = open(key_dir + "/key.pub"); public = f.read().rstrip(); f.close()
    shutil.rmtree(key_dir)
    return (private, public)


class SelfDeletingDir(str):
    def __del__(self):
        shutil.rmtree(self)
        try:
            super(SelfDeletingDir,self).__del__()
        except AttributeError:
            pass

class TeeStderr(StringIO):
    stderr = None
    def __init__(self):
        StringIO.__init__(self)
        self.stderr = sys.stderr
        self.logger = logging.getLogger('root')
        sys.stderr = self
    def __del__(self):
        sys.stderr = self.stderr
    def write(self, data):
        self.stderr.write(data)
        for l in data.split('\n'):
            self.logger.warning(l)
    def fileno(self):
        return self.stderr.fileno()
    def isatty(self):
        return self.stderr.isatty()

class TeeStdout(StringIO):
    stdout = None
    def __init__(self):
        StringIO.__init__(self)
        self.stdout = sys.stdout
        self.logger = logging.getLogger('root')
        sys.stdout = self
    def __del__(self):
        sys.stdout = self.stdout
    def write(self, data):
        self.stdout.write(data)
        for l in data.split('\n'):
            self.logger.info(l)
    def fileno(self):
        return self.stdout.fileno()
    def isatty(self):
        return self.stdout.isatty()


# Borrowed from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python.
def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    raise Exception("program ‘{0}’ not found in \$PATH".format(program))

def enum(**enums):
    return type('Enum', (), enums)


########NEW FILE########
__FILENAME__ = generic_deployment_test
import os
import subprocess
import nixops.statefile

from nose import SkipTest

from tests.functional import DatabaseUsingTest

class GenericDeploymentTest(DatabaseUsingTest):
    def setup(self):
        super(GenericDeploymentTest,self).setup()
        self.depl = self.sf.create_deployment()
        self.depl.logger.set_autoresponse("y")

########NEW FILE########
__FILENAME__ = single_machine_test
from os import path

from nose import tools

from tests.functional import generic_deployment_test

parent_dir = path.dirname(__file__)

logical_spec = '%s/single_machine_logical_base.nix' % (parent_dir)

class SingleMachineTest(generic_deployment_test.GenericDeploymentTest):
    _multiprocess_can_split_ = True

    def setup(self):
        super(SingleMachineTest,self).setup()
        self.depl.nix_exprs = [ logical_spec ]

    def test_ec2(self):
        self.depl.nix_exprs = self.depl.nix_exprs + [
            ('%s/single_machine_ec2_base.nix' % (parent_dir))
        ]
        self.run_check()

    def check_command(self, command):
        self.depl.evaluate()
        machine = self.depl.machines.values()[0]
        return machine.run_command(command)

########NEW FILE########
__FILENAME__ = test_backups
import time

from os import path

from nose import tools

from tests.functional import generic_deployment_test

parent_dir = path.dirname(__file__)

logical_spec = '%s/single_machine_logical_base.nix' % (parent_dir)

class TestBackups(generic_deployment_test.GenericDeploymentTest):
    _multiprocess_can_split_ = True

    def setup(self):
        super(TestBackups,self).setup()
        self.depl.nix_exprs = [ logical_spec,
                '%s/single_machine_ec2_ebs.nix' % (parent_dir),
                '%s/single_machine_ec2_base.nix' % (parent_dir)
                ]

    def backup_and_restore_path(self, path=""):
        self.depl.deploy()
        self.check_command("echo -n important-data > %s/back-me-up" % (path))
        backup_id = self.depl.backup()
        backups = self.depl.get_backups()
        while backups[backup_id]['status'] == "running":
            time.sleep(10)
            backups = self.depl.get_backups()
        self.check_command("rm %s/back-me-up" % (path))
        self.depl.restore(backup_id=backup_id)
        self.check_command("echo -n important-data | diff %s/back-me-up -" % (path))

    def test_simple_restore(self):
        self.backup_and_restore_path()

    def test_raid_restore(self):
        self.depl.nix_exprs = self.depl.nix_exprs + [ '%s/single_machine_ec2_raid-0.nix' % (parent_dir) ]
        self.backup_and_restore_path("/data")

    def check_command(self, command):
        self.depl.evaluate()
        machine = self.depl.machines.values()[0]
        return machine.run_command(command)

########NEW FILE########
__FILENAME__ = test_cloning_clones
from nose import tools

from tests.functional import single_machine_test

class TestCloningClones(single_machine_test.SingleMachineTest):
    def run_check(self):
        depl = self.depl.clone()
        tools.assert_equal(depl.nix_exprs, self.depl.nix_exprs)
        tools.assert_equal(depl.nix_path, self.depl.nix_path)
        tools.assert_equal(depl.args, self.depl.args)

########NEW FILE########
__FILENAME__ = test_deleting_deletes
from nose import tools
from nixops import deployment

from tests.functional import single_machine_test

class TestDeletingDeletes(single_machine_test.SingleMachineTest):
    def run_check(self):
        uuid = self.depl.uuid
        self.depl.delete()
        tools.assert_raises(Exception, self.sf.open_deployment, (uuid,))

########NEW FILE########
__FILENAME__ = test_deploys_nixos
from nose import tools

from tests.functional import single_machine_test

class TestDeploysNixos(single_machine_test.SingleMachineTest):
    def run_check(self):
        self.depl.deploy()
        self.check_command("test -f /etc/NIXOS")

########NEW FILE########
__FILENAME__ = test_deploys_spot_instance
from nose import tools
from tests.functional import single_machine_test
from os import path

parent_dir = path.dirname(__file__)

class TestDeploysSpotInstance(single_machine_test.SingleMachineTest):
    def run_check(self):
        self.depl.nix_exprs = self.depl.nix_exprs + [
                '%s/single_machine_ec2_spot_instance.nix' % (parent_dir),
                ]
        self.depl.deploy()
        self.check_command("test -f /etc/NIXOS")

########NEW FILE########
__FILENAME__ = test_encrypted_links
from os import path
from nose import tools, SkipTest
from tests.functional import generic_deployment_test
from nixops.ssh_util import SSHCommandFailed
from nixops.util import devnull
import sys
import time
import signal
import subprocess

parent_dir = path.dirname(__file__)

logical_spec = '%s/encrypted-links.nix' % (parent_dir)

class TestEncryptedLinks(generic_deployment_test.GenericDeploymentTest):

    def setup(self):
        super(TestEncryptedLinks,self).setup()
        self.depl.nix_exprs = [ logical_spec ]

    def test_deploy(self):
        if subprocess.call(["VBoxManage", "--version"],
                           stdout=devnull,
                           stderr=devnull) != 0:
            raise SkipTest("VirtualBox is not available")

        self.depl.debug = True
        self.depl.deploy()

        # !!! Shouldn't need this, instead the encrypted links target
        # should wait until the link is active...
        time.sleep(1)
        self.ping("machine1", "machine2")
        self.ping("machine2", "machine1")
        self.depl.machines["machine1"].run_command("systemctl stop encrypted-links.target")
        with tools.assert_raises(SSHCommandFailed):
            self.ping("machine1", "machine2")
        with tools.assert_raises(SSHCommandFailed):
            self.ping("machine2", "machine1")

    def ping(self, machine1, machine2):
        self.depl.machines[machine1].run_command("ping -c1 {0}-encrypted".format(machine2))

########NEW FILE########
__FILENAME__ = test_invalid_identifier
from os import path

from nose import tools
from nose.tools import raises
from tests.functional import generic_deployment_test

parent_dir = path.dirname(__file__)

logical_spec = '%s/invalid-identifier.nix' % (parent_dir)

class TestInvalidIdentifier(generic_deployment_test.GenericDeploymentTest):

    def setup(self):
        super(TestInvalidIdentifier,self).setup()
        self.depl.nix_exprs = [ logical_spec ]

    @raises(Exception)
    def test_invalid_identifier_fails_evaluation(self):
        self.depl.evaluate()


########NEW FILE########
__FILENAME__ = test_query_deployments
from nose import tools

from tests.functional import DatabaseUsingTest

class TestQueryDeployments(DatabaseUsingTest):
    def test_shows_all_deployments(self):
        depls = []
        for i in range(10):
            depls.append(self.sf.create_deployment())
        uuids = self.sf.query_deployments()
        for depl in depls:
            tools.assert_true(any([ depl.uuid == uuid for uuid in uuids ]))

########NEW FILE########
__FILENAME__ = test_rebooting_reboots
from nose import tools

from tests.functional import single_machine_test

from nixops.ssh_util import SSHCommandFailed

class TestRebootingReboots(single_machine_test.SingleMachineTest):
    def run_check(self):
        self.depl.deploy()
        self.check_command("touch /run/not-rebooted")
        self.depl.reboot_machines(wait=True)
        m = self.depl.active.values()[0]
        m.check()
        tools.assert_equal(m.state, m.UP)
        with tools.assert_raises(SSHCommandFailed):
            self.check_command("test -f /run/not-rebooted")

########NEW FILE########
__FILENAME__ = test_rollback_rollsback
from os import path
from nose import tools

from tests.functional import single_machine_test

from nixops.ssh_util import SSHCommandFailed

parent_dir = path.dirname(__file__)

has_hello_spec = '%s/single_machine_has_hello.nix' % (parent_dir)

rollback_spec = '%s/single_machine_rollback.nix' % (parent_dir)

class TestRollbackRollsback(single_machine_test.SingleMachineTest):
    _multiprocess_can_split_ = True

    def setup(self):
        super(TestRollbackRollsback,self).setup()
        self.depl.nix_exprs = self.depl.nix_exprs + [ rollback_spec ]

    def run_check(self):
        self.depl.deploy()
        with tools.assert_raises(SSHCommandFailed):
            self.check_command("hello")
        self.depl.nix_exprs = self.depl.nix_exprs + [ has_hello_spec ]
        self.depl.deploy()
        self.check_command("hello")
        self.depl.rollback(generation=1)
        with tools.assert_raises(SSHCommandFailed):
            self.check_command("hello")

########NEW FILE########
__FILENAME__ = test_send_keys_sends_keys
from os import path
from nose import tools

from tests.functional import single_machine_test

parent_dir = path.dirname(__file__)

secret_key_spec = '%s/single_machine_secret_key.nix' % (parent_dir)

class TestSendKeysSendsKeys(single_machine_test.SingleMachineTest):
    _multiprocess_can_split_ = True

    def setup(self):
        super(TestSendKeysSendsKeys,self).setup()
        self.depl.nix_exprs = self.depl.nix_exprs + [ secret_key_spec ]

    def run_check(self):
        self.depl.deploy()
        self.check_command("test -f /run/keys/secret.key")
        self.check_command("rm -f /run/keys/secret.key")
        self.depl.send_keys()
        self.check_command("test -f /run/keys/secret.key")

########NEW FILE########
__FILENAME__ = test_starting_starts
from nose import tools

from tests.functional import single_machine_test

class TestStartingStarts(single_machine_test.SingleMachineTest):
    def run_check(self):
        self.depl.deploy()
        self.depl.stop_machines()
        self.depl.start_machines()
        m = self.depl.active.values()[0]
        m.check()
        tools.assert_equal(m.state, m.UP)

########NEW FILE########
__FILENAME__ = test_stopping_stops
from nose import tools

from tests.functional import single_machine_test

class TestStoppingStops(single_machine_test.SingleMachineTest):
    def run_check(self):
        self.depl.deploy()
        self.depl.stop_machines()
        m = self.depl.active.values()[0]
        m.check()
        tools.assert_equal(m.state, m.STOPPED)

########NEW FILE########
__FILENAME__ = test_logger
import unittest

from StringIO import StringIO

from nixops.logger import Logger

class RootLoggerTest(unittest.TestCase):
    def setUp(self):
        self.logfile = StringIO()
        self.root_logger = Logger(self.logfile)

    def assert_log(self, value):
        self.assertEquals(self.logfile.getvalue(), value)

    def test_simple(self):
        self.root_logger.log("line1")
        self.assert_log("line1\n")
        self.root_logger.log("line2")
        self.assert_log("line1\nline2\n")

    def test_prefix(self):
        self.root_logger.log_start("xxx: ", "foo")
        self.root_logger.log_end("xxx: ", "bar")
        self.assert_log("xxx: foobar\n")

    def test_prefix_mixed(self):
        self.root_logger.log_start("xxx: ", "begin1")
        self.root_logger.log_start("yyy: ", "begin2")
        self.root_logger.log_end("xxx: ", "end1")
        self.root_logger.log_end("yyy: ", "end2")
        self.assert_log("xxx: begin1\nyyy: begin2\nxxx: end1\nyyy: end2\n")

class MachineLoggerTest(RootLoggerTest):
    def setUp(self):
        RootLoggerTest.setUp(self)
        self.m1_logger = self.root_logger.get_logger_for("machine1")
        self.m2_logger = self.root_logger.get_logger_for("machine2")

    def test_simple(self):
        self.m2_logger.success("success!")
        self.m1_logger.warn("warning!")
        self.assert_log("machine2> success!\nmachine1> warning: warning!\n")

    def test_continue(self):
        self.m1_logger.log_start("Begin...")
        for dummy in range(10):
            self.m1_logger.log_continue(".")
        self.m1_logger.log_end("end.")
        self.assert_log("machine1> Begin.............end.\n")

    def test_continue_mixed(self):
        self.m1_logger.log_start("Begin 1...")
        self.m2_logger.log_start("Begin 2...")

        for dummy in range(10):
            self.m1_logger.log_continue(".")
            self.m2_logger.log_continue(".")

        self.m1_logger.log_end("end 1.")
        self.m2_logger.log_end("end 2.")
        self.assert_log("machine1> Begin 1...\nmachine2> Begin 2...\n"
                        "machine1> .\nmachine2> .\nmachine1> .\nmachine2> .\n"
                        "machine1> .\nmachine2> .\nmachine1> .\nmachine2> .\n"
                        "machine1> .\nmachine2> .\nmachine1> .\nmachine2> .\n"
                        "machine1> .\nmachine2> .\nmachine1> .\nmachine2> .\n"
                        "machine1> .\nmachine2> .\nmachine1> .\nmachine2> .\n"
                        "machine1> end 1.\nmachine2> end 2.\n")

########NEW FILE########
__FILENAME__ = test_nix_expr
import unittest

from textwrap import dedent

from nixops.nix_expr import py2nix, nix2py, nixmerge
from nixops.nix_expr import RawValue, Function

__all__ = ['Py2NixTest', 'Nix2PyTest', 'NixMergeTest']


class Py2NixTestBase(unittest.TestCase):
    def assert_nix(self, nix_expr, expected, maxwidth=80, inline=False):
        result = py2nix(nix_expr, maxwidth=maxwidth, inline=inline)
        self.assertEqual(
            result, expected,
            "Expected:\n{0}\nGot:\n{1}".format(expected, result)
        )

    def test_numeric(self):
        self.assert_nix(123, "123")
        self.assert_nix(-123, "builtins.sub 0 123")
        self.assertRaises(ValueError, py2nix, 123.4)

    def test_boolean(self):
        self.assert_nix(True, "true")
        self.assert_nix(False, "false")

    def test_null(self):
        self.assert_nix(None, "null")

    def test_invalid(self):
        self.assertRaises(ValueError, py2nix, lambda: 123)
        self.assertRaises(ValueError, py2nix, Exception)

    def test_empty(self):
        self.assert_nix("", "\"\"")
        self.assert_nix({}, "{}")
        self.assert_nix([], "[]")

    def test_string(self):
        self.assert_nix("xyz", '"xyz"')
        self.assert_nix("a'b\"c", r'''"a'b\"c"''')
        self.assert_nix("abc\ndef\nghi", r'"abc\ndef\nghi"')
        self.assert_nix("abc\ndef\nghi\n", "''\n  abc\n  def\n  ghi\n''",
                        maxwidth=0)
        self.assert_nix("\\foo", r'"\\foo"')
        self.assert_nix("xx${yy}zz", r'"xx\${yy}zz"')
        self.assert_nix("xx\n${yy}\nzz\n", "''\n  xx\n  ''${yy}\n  zz\n''",
                        maxwidth=0)
        self.assert_nix("xx\n''yy\nzz\n", "''\n  xx\n  '''yy\n  zz\n''",
                        maxwidth=0)

    def test_raw_value(self):
        self.assert_nix({'a': RawValue('import <something>')},
                        '{ a = import <something>; }')
        self.assert_nix([RawValue("!")], '[ ! ]')

    def test_list(self):
        self.assert_nix([1, 2, 3], '[ 1 2 3 ]')
        self.assert_nix(["a", "b", "c"], '[ "a" "b" "c" ]')
        self.assert_nix(["a\na\na\n", "b\nb\n", "c"],
                        r'[ "a\na\na\n" "b\nb\n" "c" ]')
        self.assert_nix(["a\na\na\n", "b\nb\n", "c"],
                        '[\n  "a\\na\\na\\n"\n  "b\\nb\\n"\n  "c"\n]',
                        maxwidth=15)

    def test_nested_list(self):
        match = dedent('''
        [
          [ 1 2 3 ]
          [ 4 5 6 ]
          [
            [
              6
              6
              6
            ]
            [
              [
                7
                7
                7
              ]
              [
                8
                8
                8
              ]
              [
                9
                9
                9
              ]
            ]
          ]
        ]
        ''').strip()

        self.assert_nix([
            [1, 2, 3],
            [4, 5, 6],
            [[6, 6, 6], [[7, 7, 7], [8, 8, 8], [9, 9, 9]]]
        ], match, maxwidth=12)

    def test_nested_singletons(self):
        match = dedent('''
        [ [ [
          1
          2
          [ [ 3 ] ]
        ] ] ]
        ''').strip()

        self.assert_nix([[[1, 2, [[3]]]]], match, maxwidth=12)

    def test_attrkeys(self):
        self.assert_nix({'aAa': 123}, '{ aAa = 123; }')
        self.assert_nix({'a.a': 123}, '{ "a.a" = 123; }')
        self.assert_nix({'\\': 123}, r'{ "\\" = 123; }')
        self.assert_nix({'a1': 123}, '{ a1 = 123; }')
        self.assert_nix({'1a': 123}, '{ "1a" = 123; }')
        self.assert_nix({'_aA': 123}, '{ _aA = 123; }')
        self.assertRaises(KeyError, py2nix, {'': 123})
        self.assertRaises(KeyError, py2nix, {123: 123})

    def test_attrvalues(self):
        self.assert_nix({'a': "abc"}, '{ a = "abc"; }')
        self.assert_nix({'a': "a\nb\nc\n"}, r'{ a = "a\nb\nc\n"; }')
        self.assert_nix({'A': [1, 2, 3]}, r'{ A = [ 1 2 3 ]; }')

    def test_nested_attrsets(self):
        match = dedent('''
        {
          aaa = {
            bbb.ccc = 123;
            cCc = 456;
          };
          xxx = [
            1
            2
            3
          ];
          yyy.y1.y2.y3 = [
            "a"
            "b"
            {
              c = "d";
            }
          ];
        }
        ''').strip()

        self.assert_nix({
            'aaa': {
                'bbb': {
                    'ccc': 123,
                },
                'cCc': 456,
            },
            'xxx': [1, 2, 3],
            'yyy': {
                'y1': {'y2': {'y3': ["a", "b", {'c': 'd'}]}},
            },
        }, match, maxwidth=0)

        self.assert_nix({'fileSystems': {
            '/': {'fsType': 'btrfs', 'label': 'root'}
        }}, '{ fileSystems."/" = { fsType = "btrfs"; label = "root"; }; }')

    def test_functions(self):
        self.assert_nix(Function("Aaa", RawValue("bbb")),
                        "Aaa: bbb")
        self.assert_nix(Function("{ ... }", [1, 2, 3]),
                        "{ ... }: [ 1 2 3 ]")
        self.assert_nix(Function("{ ... }", "a\nb\nc\n"),
                        r'{ ... }: "a\nb\nc\n"')
        self.assert_nix(Function("{ ... }", "a\nb\nc\n"),
                        "{ ... }: ''\n  a\n  b\n  c\n''", maxwidth=0)
        self.assert_nix(Function("xxx", {'a': {'b': 'c'}}),
                        'xxx: {\n  a.b = "c";\n}', maxwidth=0)

    def test_nested_functions(self):
        match = dedent('''
        { config, pkgs, ... }: {
          a.b.c = 1;
          b.c.d = 2;
          d.e = [ "e" "f" ];
          e = f: {
            x = ''
              aaa
              bbb
              ccc
            '';
          };
        }
        ''').strip()

        self.assert_nix(Function(
            "{ config, pkgs, ... }",
            {'a': {'b': {'c': 1}},
             'b': {'c': {'d': 2}},
             'd': {'e': ['e', 'f']},
             'e': Function('f', {
                 'x': "aaa\nbbb\nccc\n"
             })}
        ), match, maxwidth=26)

    def test_function_call(self):
        self.assert_nix(Function("fun_call", {'a': 'b'}, call=True),
                        'fun_call { a = "b"; }')
        self.assert_nix(Function("multiline_call", {'a': 'b'}, call=True),
                        'multiline_call {\n  a = "b";\n}', maxwidth=0)

    def test_stacked_attrs(self):
        self.assert_nix({('a', 'b'): 'c', ('d'): 'e'},
                        '{ a.b = "c"; d = "e"; }')
        self.assert_nix({'a': {('b', 'c'): {}}, ('a', 'b', 'c', 'd'): 'x'},
                        '{ a.b.c.d = "x"; }')
        self.assert_nix({('a', 'a'): 1, ('a', 'b'): 2, 'a': {'c': 3}},
                        '{ a = { a = 1; b = 2; c = 3; }; }')
        self.assert_nix({('a', 'b'): [1, 2], 'a': {'b': [3, 4]}},
                        '{ a.b = [ 1 2 3 4 ]; }')

        # a more real-world example
        self.assert_nix({
            ('services', 'xserver'): {
                'enable': True,
                'layout': 'dvorak',
                ('windowManager', 'default'): 'i3',
                ('windowManager', 'i3'): {
                    'enable': True,
                    'configFile': '/somepath',
                },
                ('desktopManager', 'default'): 'none',
                'desktopManager': {'e17': {'enable': True}},
            }
        }, dedent('''
            {
              services.xserver = {
                desktopManager = { default = "none"; e17.enable = true; };
                enable = true;
                layout = "dvorak";
                windowManager = {
                  default = "i3";
                  i3 = { configFile = "/somepath"; enable = true; };
                };
              };
            }
        ''').strip())

        self.assertRaises(KeyError, py2nix, {(): 1})
        self.assertRaises(ValueError, py2nix, {('a', 'b'): 1, 'a': 2})

    def test_inline(self):
        self.assert_nix({'foo': ['a\nb\nc\n'], 'bar': ['d\ne\nf\n']},
                        r'{ bar = [ "d\ne\nf\n" ]; foo = [ "a\nb\nc\n" ]; }',
                        inline=True, maxwidth=0)
        self.assert_nix({"a\nb": ["c", "d"], "e\nf": ["g", "h"]},
                        r'{ "a\nb" = [ "c" "d" ]; "e\nf" = [ "g" "h" ]; }',
                        inline=True, maxwidth=0)

    def test_list_compound(self):
        self.assert_nix([Function("123 //", 456, call=True),
                         RawValue("a b c")],
                        '[ (123 // 456) (a b c) ]')
        self.assert_nix([RawValue("a b c"), {
            'cde': [RawValue("1,2,3"), RawValue("4 5 6"), RawValue("7\n8\n9")]
        }], '[ (a b c) { cde = [ 1,2,3 (4 5 6) (7\n8\n9) ]; } ]')


class Nix2PyTest(unittest.TestCase):
    def test_simple(self):
        self.assertEquals(py2nix(nix2py('{\na = b;\n}'), maxwidth=0),
                          '{\na = b;\n}')
        self.assertEquals(py2nix(nix2py('\n{\na = b;\n}\n'), maxwidth=0),
                          '{\na = b;\n}')

    def test_nested(self):
        self.assertEquals(py2nix([nix2py('a\nb\nc')], maxwidth=0),
                          '[\n  (a\n  b\n  c)\n]')
        self.assertEquals(py2nix({'foo': nix2py('a\nb\nc'),
                                  'bar': nix2py('d\ne\nf')}, maxwidth=0),
                          # ugly, but probably won't happen in practice
                          '{\n  bar = d\n  e\n  f;\n  foo = a\n  b\n  c;\n}')


class NixMergeTest(unittest.TestCase):
    def assert_merge(self, sources, expect):
        self.assertEqual(reduce(nixmerge, sources), expect)

    def test_merge_list(self):
        self.assert_merge([
            [1, 2, 3],
            [4, 5, 6],
            [7, 6, 5],
            ["abc", "def"],
            ["ghi", "abc"],
        ], [1, 2, 3, 4, 5, 6, 7, "abc", "ghi", "def"])

    def test_merge_dict(self):
        self.assert_merge([
            {},
            {'a': {'b': {'c': 'd'}}},
            {'a': {'c': 'e'}},
            {'b': {'a': ['a']}},
            {'b': {'a': ['b']}},
            {'b': {'A': ['B']}},
            {'e': 'f'},
            {},
        ], {
            'a': {
                'c': 'e',
                'b': {'c': 'd'}
            },
            'b': {'a': ['a', 'b'],
                  'A': ['B']},
            'e': 'f',
        })

    def test_unhashable(self):
        self.assertRaises(TypeError, nixmerge, [[1]], [[2]])
        self.assertRaises(TypeError, nixmerge, [{'x': 1}], [{'y': 2}])

    def test_invalid(self):
        self.assertRaises(ValueError, nixmerge, [123], {'a': 456})
        self.assertRaises(ValueError, nixmerge, "a", "b")
        self.assertRaises(ValueError, nixmerge, 123, 456)
        self.assertRaises(ValueError, nixmerge, RawValue("a"), RawValue("b"))
        self.assertRaises(ValueError, nixmerge,
                          Function("aaa", {'a': 1}), Function("ccc", {'b': 2}))
        self.assertRaises(ValueError, nixmerge,
                          Function("aaa", {'a': 1}), {'b': 2})

########NEW FILE########
__FILENAME__ = tests
import nose
import sys
import os

if __name__ == "__main__":
    config = nose.config.Config(plugins=nose.plugins.manager.DefaultPluginManager())
    config.configure(argv=[sys.argv[0], "-e", "^coverage-tests\.py$"] +
                     sys.argv[1:])
    count = nose.loader.defaultTestLoader(config=config).loadTestsFromNames(['.']).countTestCases()
    nose.main(argv=[sys.argv[0],
                    "--process-timeout=inf",
                    "--processes=%d".format(count),
                    "-e", "^coverage-tests\.py$"] + sys.argv[1:])

########NEW FILE########
