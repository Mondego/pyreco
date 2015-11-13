__FILENAME__ = models
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping
from moto.core import BaseBackend
from moto.ec2 import ec2_backend

# http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/AS_Concepts.html#Cooldown
DEFAULT_COOLDOWN = 300


class FakeScalingPolicy(object):
    def __init__(self, name, adjustment_type, as_name, scaling_adjustment,
                 cooldown):
        self.name = name
        self.adjustment_type = adjustment_type
        self.as_name = as_name
        self.scaling_adjustment = scaling_adjustment
        if cooldown is not None:
            self.cooldown = cooldown
        else:
            self.cooldown = DEFAULT_COOLDOWN

    def execute(self):
        if self.adjustment_type == 'ExactCapacity':
            autoscaling_backend.set_desired_capacity(self.as_name, self.scaling_adjustment)
        elif self.adjustment_type == 'ChangeInCapacity':
            autoscaling_backend.change_capacity(self.as_name, self.scaling_adjustment)
        elif self.adjustment_type == 'PercentChangeInCapacity':
            autoscaling_backend.change_capacity_percent(self.as_name, self.scaling_adjustment)


class FakeLaunchConfiguration(object):
    def __init__(self, name, image_id, key_name, security_groups, user_data,
                 instance_type, instance_monitoring, instance_profile_name,
                 spot_price, ebs_optimized, associate_public_ip_address, block_device_mapping_dict):
        self.name = name
        self.image_id = image_id
        self.key_name = key_name
        self.security_groups = security_groups if security_groups else []
        self.user_data = user_data
        self.instance_type = instance_type
        self.instance_monitoring = instance_monitoring
        self.instance_profile_name = instance_profile_name
        self.spot_price = spot_price
        self.ebs_optimized = ebs_optimized
        self.associate_public_ip_address = associate_public_ip_address
        self.block_device_mapping_dict = block_device_mapping_dict

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        instance_profile_name = properties.get("IamInstanceProfile")

        config = autoscaling_backend.create_launch_configuration(
            name=resource_name,
            image_id=properties.get("ImageId"),
            key_name=properties.get("KeyName"),
            security_groups=properties.get("SecurityGroups"),
            user_data=properties.get("UserData"),
            instance_type=properties.get("InstanceType"),
            instance_monitoring=properties.get("InstanceMonitoring"),
            instance_profile_name=instance_profile_name,
            spot_price=properties.get("SpotPrice"),
            ebs_optimized=properties.get("EbsOptimized"),
            associate_public_ip_address=properties.get("AssociatePublicIpAddress"),
            block_device_mappings=properties.get("BlockDeviceMapping.member")
        )
        return config

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def block_device_mappings(self):
        if not self.block_device_mapping_dict:
            return None
        else:
            return self._parse_block_device_mappings()

    @property
    def instance_monitoring_enabled(self):
        if self.instance_monitoring:
            return 'true'
        return 'false'

    def _parse_block_device_mappings(self):
        block_device_map = BlockDeviceMapping()
        for mapping in self.block_device_mapping_dict:
            block_type = BlockDeviceType()
            mount_point = mapping.get('device_name')
            if 'ephemeral' in mapping.get('virtual_name', ''):
                block_type.ephemeral_name = mapping.get('virtual_name')
            else:
                block_type.volume_type = mapping.get('ebs._volume_type')
                block_type.snapshot_id = mapping.get('ebs._snapshot_id')
                block_type.delete_on_termination = mapping.get('ebs._delete_on_termination')
                block_type.size = mapping.get('ebs._volume_size')
                block_type.iops = mapping.get('ebs._iops')
            block_device_map[mount_point] = block_type
        return block_device_map


class FakeAutoScalingGroup(object):
    def __init__(self, name, availability_zones, desired_capacity, max_size,
                 min_size, launch_config_name, vpc_zone_identifier,
                 default_cooldown, health_check_period, health_check_type,
                 load_balancers, placement_group, termination_policies):
        self.name = name
        self.availability_zones = availability_zones
        self.max_size = max_size
        self.min_size = min_size

        self.launch_config = autoscaling_backend.launch_configurations[launch_config_name]
        self.launch_config_name = launch_config_name
        self.vpc_zone_identifier = vpc_zone_identifier

        self.default_cooldown = default_cooldown if default_cooldown else DEFAULT_COOLDOWN
        self.health_check_period = health_check_period
        self.health_check_type = health_check_type if health_check_type else "EC2"
        self.load_balancers = load_balancers
        self.placement_group = placement_group
        self.termination_policies = termination_policies

        self.instances = []
        self.set_desired_capacity(desired_capacity)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        launch_config_name = properties.get("LaunchConfigurationName")
        load_balancer_names = properties.get("LoadBalancerNames", [])

        group = autoscaling_backend.create_autoscaling_group(
            name=resource_name,
            availability_zones=properties.get("AvailabilityZones", []),
            desired_capacity=properties.get("DesiredCapacity"),
            max_size=properties.get("MaxSize"),
            min_size=properties.get("MinSize"),
            launch_config_name=launch_config_name,
            vpc_zone_identifier=properties.get("VPCZoneIdentifier"),
            default_cooldown=properties.get("Cooldown"),
            health_check_period=properties.get("HealthCheckGracePeriod"),
            health_check_type=properties.get("HealthCheckType"),
            load_balancers=load_balancer_names,
            placement_group=None,
            termination_policies=properties.get("TerminationPolicies", []),
        )
        return group

    @property
    def physical_resource_id(self):
        return self.name

    def update(self, availability_zones, desired_capacity, max_size, min_size,
               launch_config_name, vpc_zone_identifier, default_cooldown,
               health_check_period, health_check_type, load_balancers,
               placement_group, termination_policies):
        self.availability_zones = availability_zones
        self.max_size = max_size
        self.min_size = min_size

        self.launch_config = autoscaling_backend.launch_configurations[launch_config_name]
        self.launch_config_name = launch_config_name
        self.vpc_zone_identifier = vpc_zone_identifier
        self.health_check_period = health_check_period
        self.health_check_type = health_check_type

        self.set_desired_capacity(desired_capacity)

    def set_desired_capacity(self, new_capacity):
        if new_capacity is None:
            self.desired_capacity = self.min_size
        else:
            self.desired_capacity = new_capacity

        curr_instance_count = len(self.instances)

        if self.desired_capacity == curr_instance_count:
            return

        if self.desired_capacity > curr_instance_count:
            # Need more instances
            count_needed = self.desired_capacity - curr_instance_count
            reservation = ec2_backend.add_instances(
                self.launch_config.image_id,
                count_needed,
                self.launch_config.user_data,
                self.launch_config.security_groups,
            )
            for instance in reservation.instances:
                instance.autoscaling_group = self
            self.instances.extend(reservation.instances)
        else:
            # Need to remove some instances
            count_to_remove = curr_instance_count - self.desired_capacity
            instances_to_remove = self.instances[:count_to_remove]
            instance_ids_to_remove = [instance.id for instance in instances_to_remove]
            ec2_backend.terminate_instances(instance_ids_to_remove)
            self.instances = self.instances[count_to_remove:]


class AutoScalingBackend(BaseBackend):

    def __init__(self):
        self.autoscaling_groups = {}
        self.launch_configurations = {}
        self.policies = {}

    def create_launch_configuration(self, name, image_id, key_name,
                                    security_groups, user_data, instance_type,
                                    instance_monitoring, instance_profile_name,
                                    spot_price, ebs_optimized, associate_public_ip_address, block_device_mappings):
        launch_configuration = FakeLaunchConfiguration(
            name=name,
            image_id=image_id,
            key_name=key_name,
            security_groups=security_groups,
            user_data=user_data,
            instance_type=instance_type,
            instance_monitoring=instance_monitoring,
            instance_profile_name=instance_profile_name,
            spot_price=spot_price,
            ebs_optimized=ebs_optimized,
            associate_public_ip_address=associate_public_ip_address,
            block_device_mapping_dict=block_device_mappings,
        )
        self.launch_configurations[name] = launch_configuration
        return launch_configuration

    def describe_launch_configurations(self, names):
        configurations = self.launch_configurations.values()
        if names:
            return [configuration for configuration in configurations if configuration.name in names]
        else:
            return configurations

    def delete_launch_configuration(self, launch_configuration_name):
        self.launch_configurations.pop(launch_configuration_name, None)

    def create_autoscaling_group(self, name, availability_zones,
                                 desired_capacity, max_size, min_size,
                                 launch_config_name, vpc_zone_identifier,
                                 default_cooldown, health_check_period,
                                 health_check_type, load_balancers,
                                 placement_group, termination_policies):

        def make_int(value):
            return int(value) if value is not None else value

        max_size = make_int(max_size)
        min_size = make_int(min_size)
        default_cooldown = make_int(default_cooldown)
        health_check_period = make_int(health_check_period)

        group = FakeAutoScalingGroup(
            name=name,
            availability_zones=availability_zones,
            desired_capacity=desired_capacity,
            max_size=max_size,
            min_size=min_size,
            launch_config_name=launch_config_name,
            vpc_zone_identifier=vpc_zone_identifier,
            default_cooldown=default_cooldown,
            health_check_period=health_check_period,
            health_check_type=health_check_type,
            load_balancers=load_balancers,
            placement_group=placement_group,
            termination_policies=termination_policies,
        )
        self.autoscaling_groups[name] = group
        return group

    def update_autoscaling_group(self, name, availability_zones,
                                 desired_capacity, max_size, min_size,
                                 launch_config_name, vpc_zone_identifier,
                                 default_cooldown, health_check_period,
                                 health_check_type, load_balancers,
                                 placement_group, termination_policies):
        group = self.autoscaling_groups[name]
        group.update(availability_zones, desired_capacity, max_size,
                     min_size, launch_config_name, vpc_zone_identifier,
                     default_cooldown, health_check_period, health_check_type,
                     load_balancers, placement_group, termination_policies)
        return group

    def describe_autoscaling_groups(self, names):
        groups = self.autoscaling_groups.values()
        if names:
            return [group for group in groups if group.name in names]
        else:
            return groups

    def delete_autoscaling_group(self, group_name):
        self.autoscaling_groups.pop(group_name, None)

    def describe_autoscaling_instances(self):
        instances = []
        for group in self.autoscaling_groups.values():
            instances.extend(group.instances)
        return instances

    def set_desired_capacity(self, group_name, desired_capacity):
        group = self.autoscaling_groups[group_name]
        group.set_desired_capacity(desired_capacity)

    def change_capacity(self, group_name, scaling_adjustment):
        group = self.autoscaling_groups[group_name]
        desired_capacity = group.desired_capacity + scaling_adjustment
        self.set_desired_capacity(group_name, desired_capacity)

    def change_capacity_percent(self, group_name, scaling_adjustment):
        """ http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
        If PercentChangeInCapacity returns a value between 0 and 1,
        Auto Scaling will round it off to 1. If the PercentChangeInCapacity
        returns a value greater than 1, Auto Scaling will round it off to the
        lower value. For example, if PercentChangeInCapacity returns 12.5,
        then Auto Scaling will round it off to 12."""
        group = self.autoscaling_groups[group_name]
        percent_change = 1 + (scaling_adjustment / 100.0)
        desired_capacity = group.desired_capacity * percent_change
        if group.desired_capacity < desired_capacity < group.desired_capacity + 1:
            desired_capacity = group.desired_capacity + 1
        else:
            desired_capacity = int(desired_capacity)
        self.set_desired_capacity(group_name, desired_capacity)

    def create_autoscaling_policy(self, name, adjustment_type, as_name,
                                  scaling_adjustment, cooldown):
        policy = FakeScalingPolicy(name, adjustment_type, as_name,
                                   scaling_adjustment, cooldown)

        self.policies[name] = policy
        return policy

    def describe_policies(self):
        return self.policies.values()

    def delete_policy(self, group_name):
        self.policies.pop(group_name, None)

    def execute_policy(self, group_name):
        policy = self.policies[group_name]
        policy.execute()

autoscaling_backend = AutoScalingBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import autoscaling_backend


class AutoScalingResponse(BaseResponse):
    def _get_int_param(self, param_name):
        value = self._get_param(param_name)
        if value is not None:
            return int(value)

    def _get_list_prefix(self, param_prefix):
        results = []
        param_index = 1
        while True:
            index_prefix = "{0}.{1}.".format(param_prefix, param_index)
            new_items = {}
            for key, value in self.querystring.items():
                if key.startswith(index_prefix):
                    new_items[camelcase_to_underscores(key.replace(index_prefix, ""))] = value[0]
            if not new_items:
                break
            results.append(new_items)
            param_index += 1
        return results

    def create_launch_configuration(self):
        instance_monitoring_string = self._get_param('InstanceMonitoring.Enabled')
        if instance_monitoring_string == 'true':
            instance_monitoring = True
        else:
            instance_monitoring = False
        autoscaling_backend.create_launch_configuration(
            name=self._get_param('LaunchConfigurationName'),
            image_id=self._get_param('ImageId'),
            key_name=self._get_param('KeyName'),
            security_groups=self._get_multi_param('SecurityGroups.member'),
            user_data=self._get_param('UserData'),
            instance_type=self._get_param('InstanceType'),
            instance_monitoring=instance_monitoring,
            instance_profile_name=self._get_param('IamInstanceProfile'),
            spot_price=self._get_param('SpotPrice'),
            ebs_optimized=self._get_param('EbsOptimized'),
            associate_public_ip_address=self._get_param("AssociatePublicIpAddress"),
            block_device_mappings=self._get_list_prefix('BlockDeviceMappings.member')
        )
        template = Template(CREATE_LAUNCH_CONFIGURATION_TEMPLATE)
        return template.render()

    def describe_launch_configurations(self):
        names = self._get_multi_param('LaunchConfigurationNames')
        launch_configurations = autoscaling_backend.describe_launch_configurations(names)
        template = Template(DESCRIBE_LAUNCH_CONFIGURATIONS_TEMPLATE)
        return template.render(launch_configurations=launch_configurations)

    def delete_launch_configuration(self):
        launch_configurations_name = self.querystring.get('LaunchConfigurationName')[0]
        autoscaling_backend.delete_launch_configuration(launch_configurations_name)
        template = Template(DELETE_LAUNCH_CONFIGURATION_TEMPLATE)
        return template.render()

    def create_auto_scaling_group(self):
        autoscaling_backend.create_autoscaling_group(
            name=self._get_param('AutoScalingGroupName'),
            availability_zones=self._get_multi_param('AvailabilityZones.member'),
            desired_capacity=self._get_int_param('DesiredCapacity'),
            max_size=self._get_int_param('MaxSize'),
            min_size=self._get_int_param('MinSize'),
            launch_config_name=self._get_param('LaunchConfigurationName'),
            vpc_zone_identifier=self._get_param('VPCZoneIdentifier'),
            default_cooldown=self._get_int_param('DefaultCooldown'),
            health_check_period=self._get_int_param('HealthCheckGracePeriod'),
            health_check_type=self._get_param('HealthCheckType'),
            load_balancers=self._get_multi_param('LoadBalancerNames.member'),
            placement_group=self._get_param('PlacementGroup'),
            termination_policies=self._get_multi_param('TerminationPolicies.member'),
        )
        template = Template(CREATE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    def describe_auto_scaling_groups(self):
        names = self._get_multi_param("AutoScalingGroupNames")
        groups = autoscaling_backend.describe_autoscaling_groups(names)
        template = Template(DESCRIBE_AUTOSCALING_GROUPS_TEMPLATE)
        return template.render(groups=groups)

    def update_auto_scaling_group(self):
        autoscaling_backend.update_autoscaling_group(
            name=self._get_param('AutoScalingGroupName'),
            availability_zones=self._get_multi_param('AvailabilityZones.member'),
            desired_capacity=self._get_int_param('DesiredCapacity'),
            max_size=self._get_int_param('MaxSize'),
            min_size=self._get_int_param('MinSize'),
            launch_config_name=self._get_param('LaunchConfigurationName'),
            vpc_zone_identifier=self._get_param('VPCZoneIdentifier'),
            default_cooldown=self._get_int_param('DefaultCooldown'),
            health_check_period=self._get_int_param('HealthCheckGracePeriod'),
            health_check_type=self._get_param('HealthCheckType'),
            load_balancers=self._get_multi_param('LoadBalancerNames.member'),
            placement_group=self._get_param('PlacementGroup'),
            termination_policies=self._get_multi_param('TerminationPolicies.member'),
        )
        template = Template(UPDATE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    def delete_auto_scaling_group(self):
        group_name = self._get_param('AutoScalingGroupName')
        autoscaling_backend.delete_autoscaling_group(group_name)
        template = Template(DELETE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    def set_desired_capacity(self):
        group_name = self._get_param('AutoScalingGroupName')
        desired_capacity = self._get_int_param('DesiredCapacity')
        autoscaling_backend.set_desired_capacity(group_name, desired_capacity)
        template = Template(SET_DESIRED_CAPACITY_TEMPLATE)
        return template.render()

    def describe_auto_scaling_instances(self):
        instances = autoscaling_backend.describe_autoscaling_instances()
        template = Template(DESCRIBE_AUTOSCALING_INSTANCES_TEMPLATE)
        return template.render(instances=instances)

    def put_scaling_policy(self):
        policy = autoscaling_backend.create_autoscaling_policy(
            name=self._get_param('PolicyName'),
            adjustment_type=self._get_param('AdjustmentType'),
            as_name=self._get_param('AutoScalingGroupName'),
            scaling_adjustment=self._get_int_param('ScalingAdjustment'),
            cooldown=self._get_int_param('Cooldown'),
        )
        template = Template(CREATE_SCALING_POLICY_TEMPLATE)
        return template.render(policy=policy)

    def describe_policies(self):
        policies = autoscaling_backend.describe_policies()
        template = Template(DESCRIBE_SCALING_POLICIES_TEMPLATE)
        return template.render(policies=policies)

    def delete_policy(self):
        group_name = self._get_param('PolicyName')
        autoscaling_backend.delete_policy(group_name)
        template = Template(DELETE_POLICY_TEMPLATE)
        return template.render()

    def execute_policy(self):
        group_name = self._get_param('PolicyName')
        autoscaling_backend.execute_policy(group_name)
        template = Template(EXECUTE_POLICY_TEMPLATE)
        return template.render()


CREATE_LAUNCH_CONFIGURATION_TEMPLATE = """<CreateLaunchConfigurationResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<ResponseMetadata>
   <RequestId>7c6e177f-f082-11e1-ac58-3714bEXAMPLE</RequestId>
</ResponseMetadata>
</CreateLaunchConfigurationResponse>"""

DESCRIBE_LAUNCH_CONFIGURATIONS_TEMPLATE = """<DescribeLaunchConfigurationsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribeLaunchConfigurationsResult>
    <LaunchConfigurations>
      {% for launch_configuration in launch_configurations %}
        <member>
          <AssociatePublicIpAddress>{{ launch_configuration.associate_public_ip_address }}</AssociatePublicIpAddress>
          <SecurityGroups>
            {% for security_group in launch_configuration.security_groups %}
              <member>{{ security_group }}</member>
            {% endfor %}
          </SecurityGroups>
          <CreatedTime>2013-01-21T23:04:42.200Z</CreatedTime>
          <KernelId/>
          {% if launch_configuration.instance_profile_name %}
            <IamInstanceProfile>{{ launch_configuration.instance_profile_name }}</IamInstanceProfile>
          {% endif %}
          <LaunchConfigurationName>{{ launch_configuration.name }}</LaunchConfigurationName>
          {% if launch_configuration.user_data %}
            <UserData>{{ launch_configuration.user_data }}</UserData>
          {% else %}
            <UserData/>
          {% endif %}
          <InstanceType>m1.small</InstanceType>
          <LaunchConfigurationARN>arn:aws:autoscaling:us-east-1:803981987763:launchConfiguration:
          9dbbbf87-6141-428a-a409-0752edbe6cad:launchConfigurationName/my-test-lc</LaunchConfigurationARN>
          {% if launch_configuration.block_device_mappings %}
            <BlockDeviceMappings>
            {% for mount_point, mapping in launch_configuration.block_device_mappings.iteritems() %}
              <member>
                <DeviceName>{{ mount_point }}</DeviceName>
                {% if mapping.ephemeral_name %}
                <VirtualName>{{ mapping.ephemeral_name }}</VirtualName>
                {% else %}
                <Ebs>
                {% if mapping.snapshot_id %}
                  <SnapshotId>{{ mapping.snapshot_id }}</SnapshotId>
                {% endif %}
                {% if mapping.size %}
                  <VolumeSize>{{ mapping.size }}</VolumeSize>
                {% endif %}
                {% if mapping.iops %}
                  <Iops>{{ mapping.iops }}</Iops>
                {% endif %}
                  <DeleteOnTermination>{{ mapping.delete_on_termination }}</DeleteOnTermination>
                  <VolumeType>{{ mapping.volume_type }}</VolumeType>
                </Ebs>
                {% endif %}
              </member>
            {% endfor %}
            </BlockDeviceMappings>
          {% else %}
            <BlockDeviceMappings/>
          {% endif %}
          <ImageId>{{ launch_configuration.image_id }}</ImageId>
          {% if launch_configuration.key_name %}
            <KeyName>{{ launch_configuration.key_name }}</KeyName>
          {% else %}
            <KeyName/>
          {% endif %}
          <RamdiskId/>
          <EbsOptimized>{{ launch_configuration.ebs_optimized }}</EbsOptimized>
          <InstanceMonitoring>
            <Enabled>{{ launch_configuration.instance_monitoring_enabled }}</Enabled>
          </InstanceMonitoring>
          {% if launch_configuration.spot_price %}
            <SpotPrice>{{ launch_configuration.spot_price }}</SpotPrice>
          {% endif %}
        </member>
      {% endfor %}
    </LaunchConfigurations>
  </DescribeLaunchConfigurationsResult>
  <ResponseMetadata>
    <RequestId>d05a22f8-b690-11e2-bf8e-2113fEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeLaunchConfigurationsResponse>"""

DELETE_LAUNCH_CONFIGURATION_TEMPLATE = """<DeleteLaunchConfigurationResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>7347261f-97df-11e2-8756-35eEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteLaunchConfigurationResponse>"""

CREATE_AUTOSCALING_GROUP_TEMPLATE = """<CreateAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<ResponseMetadata>
<RequestId>8d798a29-f083-11e1-bdfb-cb223EXAMPLE</RequestId>
</ResponseMetadata>
</CreateAutoScalingGroupResponse>"""

DESCRIBE_AUTOSCALING_GROUPS_TEMPLATE = """<DescribeAutoScalingGroupsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DescribeAutoScalingGroupsResult>
    <AutoScalingGroups>
      {% for group in groups %}
      <member>
        <Tags/>
        <SuspendedProcesses/>
        <AutoScalingGroupName>{{ group.name }}</AutoScalingGroupName>
        <HealthCheckType>{{ group.health_check_type }}</HealthCheckType>
        <CreatedTime>2013-05-06T17:47:15.107Z</CreatedTime>
        <EnabledMetrics/>
        <LaunchConfigurationName>{{ group.launch_config_name }}</LaunchConfigurationName>
        <Instances/>
        <DesiredCapacity>{{ group.desired_capacity }}</DesiredCapacity>
        <AvailabilityZones>
          {% for availability_zone in group.availability_zones %}
          <member>{{ availability_zone }}</member>
          {% endfor %}
        </AvailabilityZones>
        {% if group.load_balancers %}
          <LoadBalancerNames>
          {% for load_balancer in group.load_balancers %}
            <member>{{ load_balancer }}</member>
          {% endfor %}
          </LoadBalancerNames>
        {% else %}
          <LoadBalancerNames/>
        {% endif %}
        <MinSize>{{ group.min_size }}</MinSize>
        {% if group.vpc_zone_identifier %}
          <VPCZoneIdentifier>{{ group.vpc_zone_identifier }}</VPCZoneIdentifier>
        {% else %}
          <VPCZoneIdentifier/>
        {% endif %}
        <HealthCheckGracePeriod>{{ group.health_check_period }}</HealthCheckGracePeriod>
        <DefaultCooldown>{{ group.default_cooldown }}</DefaultCooldown>
        <AutoScalingGroupARN>arn:aws:autoscaling:us-east-1:803981987763:autoScalingGroup:ca861182-c8f9-4ca7-b1eb-cd35505f5ebb
        :autoScalingGroupName/my-test-asg-lbs</AutoScalingGroupARN>
        {% if group.termination_policies %}
        <TerminationPolicies>
          {% for policy in group.termination_policies %}
          <member>{{ policy }}</member>
          {% endfor %}
        </TerminationPolicies>
        {% else %}
        <TerminationPolicies/>
        {% endif %}
        <MaxSize>{{ group.max_size }}</MaxSize>
        {% if group.placement_group %}
        <PlacementGroup>{{ group.placement_group }}</PlacementGroup>
        {% endif %}
      </member>
      {% endfor %}
    </AutoScalingGroups>
  </DescribeAutoScalingGroupsResult>
  <ResponseMetadata>
    <RequestId>0f02a07d-b677-11e2-9eb0-dd50EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeAutoScalingGroupsResponse>"""

UPDATE_AUTOSCALING_GROUP_TEMPLATE = """<UpdateAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>adafead0-ab8a-11e2-ba13-ab0ccEXAMPLE</RequestId>
  </ResponseMetadata>
</UpdateAutoScalingGroupResponse>"""

DELETE_AUTOSCALING_GROUP_TEMPLATE = """<DeleteAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>70a76d42-9665-11e2-9fdf-211deEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteAutoScalingGroupResponse>"""

DESCRIBE_AUTOSCALING_INSTANCES_TEMPLATE = """<DescribeAutoScalingInstancesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribeAutoScalingInstancesResult>
    <AutoScalingInstances>
      {% for instance in instances %}
      <member>
        <HealthStatus>HEALTHY</HealthStatus>
        <AutoScalingGroupName>{{ instance.autoscaling_group.name }}</AutoScalingGroupName>
        <AvailabilityZone>us-east-1e</AvailabilityZone>
        <InstanceId>{{ instance.id }}</InstanceId>
        <LaunchConfigurationName>{{ instance.autoscaling_group.launch_config_name }}</LaunchConfigurationName>
        <LifecycleState>InService</LifecycleState>
      </member>
      {% endfor %}
    </AutoScalingInstances>
  </DescribeAutoScalingInstancesResult>
  <ResponseMetadata>
    <RequestId>df992dc3-b72f-11e2-81e1-750aa6EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeAutoScalingInstancesResponse>"""

CREATE_SCALING_POLICY_TEMPLATE = """<PutScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <PutScalingPolicyResult>
    <PolicyARN>arn:aws:autoscaling:us-east-1:803981987763:scalingPolicy:b0dcf5e8
-02e6-4e31-9719-0675d0dc31ae:autoScalingGroupName/my-test-asg:policyName/my-scal
eout-policy</PolicyARN>
  </PutScalingPolicyResult>
  <ResponseMetadata>
    <RequestId>3cfc6fef-c08b-11e2-a697-2922EXAMPLE</RequestId>
  </ResponseMetadata>
</PutScalingPolicyResponse>"""

DESCRIBE_SCALING_POLICIES_TEMPLATE = """<DescribePoliciesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribePoliciesResult>
    <ScalingPolicies>
      {% for policy in policies %}
      <member>
        <PolicyARN>arn:aws:autoscaling:us-east-1:803981987763:scalingPolicy:c322
761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/my-test-asg:policyName/MyScaleDownPolicy</PolicyARN>
        <AdjustmentType>{{ policy.adjustment_type }}</AdjustmentType>
        <ScalingAdjustment>{{ policy.scaling_adjustment }}</ScalingAdjustment>
        <PolicyName>{{ policy.name }}</PolicyName>
        <AutoScalingGroupName>{{ policy.as_name }}</AutoScalingGroupName>
        <Cooldown>{{ policy.cooldown }}</Cooldown>
        <Alarms/>
      </member>
      {% endfor %}
    </ScalingPolicies>
  </DescribePoliciesResult>
  <ResponseMetadata>
    <RequestId>ec3bffad-b739-11e2-b38d-15fbEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribePoliciesResponse>"""

SET_DESIRED_CAPACITY_TEMPLATE = """<SetDesiredCapacityResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>9fb7e2db-6998-11e2-a985-57c82EXAMPLE</RequestId>
  </ResponseMetadata>
</SetDesiredCapacityResponse>"""

EXECUTE_POLICY_TEMPLATE = """<ExecuteScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>70a76d42-9665-11e2-9fdf-211deEXAMPLE</RequestId>
  </ResponseMetadata>
</ExecuteScalingPolicyResponse>"""

DELETE_POLICY_TEMPLATE = """<DeleteScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>70a76d42-9665-11e2-9fdf-211deEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteScalingPolicyResponse>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import AutoScalingResponse

url_bases = [
    "https?://autoscaling.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': AutoScalingResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = backends
from moto.autoscaling import autoscaling_backend
from moto.dynamodb import dynamodb_backend
from moto.dynamodb2 import dynamodb_backend2
from moto.ec2 import ec2_backend
from moto.elb import elb_backend
from moto.emr import emr_backend
from moto.s3 import s3_backend
from moto.s3bucket_path import s3bucket_path_backend
from moto.ses import ses_backend
from moto.sqs import sqs_backend
from moto.sts import sts_backend
from moto.route53 import route53_backend

BACKENDS = {
    'autoscaling': autoscaling_backend,
    'dynamodb': dynamodb_backend,
    'dynamodb2': dynamodb_backend2,
    'ec2': ec2_backend,
    'elb': elb_backend,
    'emr': emr_backend,
    's3': s3_backend,
    's3bucket_path': s3bucket_path_backend,
    'ses': ses_backend,
    'sqs': sqs_backend,
    'sts': sts_backend,
    'route53': route53_backend
}

########NEW FILE########
__FILENAME__ = models
import json

from moto.core import BaseBackend

from .parsing import ResourceMap
from .utils import generate_stack_id


class FakeStack(object):
    def __init__(self, stack_id, name, template):
        self.stack_id = stack_id
        self.name = name
        self.template = template

        template_dict = json.loads(self.template)
        self.description = template_dict.get('Description')

        self.resource_map = ResourceMap(stack_id, name, template_dict)
        self.resource_map.create()

    @property
    def stack_resources(self):
        return self.resource_map.values()


class CloudFormationBackend(BaseBackend):

    def __init__(self):
        self.stacks = {}

    def create_stack(self, name, template):
        stack_id = generate_stack_id(name)
        new_stack = FakeStack(stack_id=stack_id, name=name, template=template)
        self.stacks[stack_id] = new_stack
        return new_stack

    def describe_stacks(self, names):
        stacks = self.stacks.values()
        if names:
            return [stack for stack in stacks if stack.name in names]
        else:
            return stacks

    def list_stacks(self):
        return self.stacks.values()

    def get_stack(self, name_or_stack_id):
        if name_or_stack_id in self.stacks:
            # Lookup by stack id
            return self.stacks.get(name_or_stack_id)
        else:
            # Lookup by stack name
            return [stack for stack in self.stacks.values() if stack.name == name_or_stack_id][0]

    # def update_stack(self, name, template):
    #     stack = self.get_stack(name)
    #     stack.template = template
    #     return stack

    def delete_stack(self, name_or_stack_id):
        if name_or_stack_id in self.stacks:
            # Delete by stack id
            return self.stacks.pop(name_or_stack_id, None)
        else:
            # Delete by stack name
            stack_to_delete = [stack for stack in self.stacks.values() if stack.name == name_or_stack_id][0]
            self.delete_stack(stack_to_delete.stack_id)


cloudformation_backend = CloudFormationBackend()

########NEW FILE########
__FILENAME__ = parsing
import collections
import logging

from moto.autoscaling import models as autoscaling_models
from moto.ec2 import models as ec2_models
from moto.elb import models as elb_models
from moto.iam import models as iam_models
from moto.sqs import models as sqs_models

MODEL_MAP = {
    "AWS::AutoScaling::AutoScalingGroup": autoscaling_models.FakeAutoScalingGroup,
    "AWS::AutoScaling::LaunchConfiguration": autoscaling_models.FakeLaunchConfiguration,
    "AWS::EC2::EIP": ec2_models.ElasticAddress,
    "AWS::EC2::Instance": ec2_models.Instance,
    "AWS::EC2::InternetGateway": ec2_models.InternetGateway,
    "AWS::EC2::Route": ec2_models.Route,
    "AWS::EC2::RouteTable": ec2_models.RouteTable,
    "AWS::EC2::SecurityGroup": ec2_models.SecurityGroup,
    "AWS::EC2::Subnet": ec2_models.Subnet,
    "AWS::EC2::SubnetRouteTableAssociation": ec2_models.SubnetRouteTableAssociation,
    "AWS::EC2::Volume": ec2_models.Volume,
    "AWS::EC2::VolumeAttachment": ec2_models.VolumeAttachment,
    "AWS::EC2::VPC": ec2_models.VPC,
    "AWS::EC2::VPCGatewayAttachment": ec2_models.VPCGatewayAttachment,
    "AWS::ElasticLoadBalancing::LoadBalancer": elb_models.FakeLoadBalancer,
    "AWS::IAM::InstanceProfile": iam_models.InstanceProfile,
    "AWS::IAM::Role": iam_models.Role,
    "AWS::SQS::Queue": sqs_models.Queue,
}

# Just ignore these models types for now
NULL_MODELS = [
    "AWS::CloudFormation::WaitCondition",
    "AWS::CloudFormation::WaitConditionHandle",
]

logger = logging.getLogger("moto")


def clean_json(resource_json, resources_map):
    """
    Cleanup the a resource dict. For now, this just means replacing any Ref node
    with the corresponding physical_resource_id.

    Eventually, this is where we would add things like function parsing (fn::)
    """
    if isinstance(resource_json, dict):
        if 'Ref' in resource_json:
            # Parse resource reference
            resource = resources_map[resource_json['Ref']]
            if hasattr(resource, 'physical_resource_id'):
                return resource.physical_resource_id
            else:
                return resource

        cleaned_json = {}
        for key, value in resource_json.iteritems():
            cleaned_json[key] = clean_json(value, resources_map)
        return cleaned_json
    elif isinstance(resource_json, list):
        return [clean_json(val, resources_map) for val in resource_json]
    else:
        return resource_json


def resource_class_from_type(resource_type):
    if resource_type in NULL_MODELS:
        return None
    if resource_type not in MODEL_MAP:
        logger.warning("No Moto CloudFormation support for %s", resource_type)
        return None
    return MODEL_MAP.get(resource_type)


def parse_resource(resource_name, resource_json, resources_map):
    resource_type = resource_json['Type']
    resource_class = resource_class_from_type(resource_type)
    if not resource_class:
        return None

    resource_json = clean_json(resource_json, resources_map)
    resource = resource_class.create_from_cloudformation_json(resource_name, resource_json)
    resource.type = resource_type
    resource.logical_resource_id = resource_name
    return resource


class ResourceMap(collections.Mapping):
    """
    This is a lazy loading map for resources. This allows us to create resources
    without needing to create a full dependency tree. Upon creation, each
    each resources is passed this lazy map that it can grab dependencies from.
    """

    def __init__(self, stack_id, stack_name, template):
        self._template = template
        self._resource_json_map = template['Resources']

        # Create the default resources
        self._parsed_resources = {
            "AWS::AccountId": "123456789012",
            "AWS::Region": "us-east-1",
            "AWS::StackId": stack_id,
            "AWS::StackName": stack_name,
        }

    def __getitem__(self, key):
        resource_name = key

        if resource_name in self._parsed_resources:
            return self._parsed_resources[resource_name]
        else:
            resource_json = self._resource_json_map.get(resource_name)
            new_resource = parse_resource(resource_name, resource_json, self)
            self._parsed_resources[resource_name] = new_resource
            return new_resource

    def __iter__(self):
        return iter(self.resource_names)

    def __len__(self):
        return len(self._resource_json_map)

    @property
    def resource_names(self):
        return self._resource_json_map.keys()

    def load_parameters(self):
        parameters = self._template.get('Parameters', {})
        for parameter_name, parameter in parameters.items():
            # Just initialize parameters to empty string for now.
            self._parsed_resources[parameter_name] = ""

    def create(self):
        self.load_parameters()

        # Since this is a lazy map, to create every object we just need to
        # iterate through self.
        for resource_name in self.resource_names:
            self[resource_name]

########NEW FILE########
__FILENAME__ = responses
import json

from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import cloudformation_backend


class CloudFormationResponse(BaseResponse):

    def create_stack(self):
        stack_name = self._get_param('StackName')
        stack_body = self._get_param('TemplateBody')

        stack = cloudformation_backend.create_stack(
            name=stack_name,
            template=stack_body,
        )
        stack_body = {
            'CreateStackResponse': {
                'CreateStackResult': {
                    'StackId': stack.name,
                }
            }
        }
        return json.dumps(stack_body)

    def describe_stacks(self):
        names = [value[0] for key, value in self.querystring.items() if "StackName" in key]
        stacks = cloudformation_backend.describe_stacks(names)

        template = Template(DESCRIBE_STACKS_TEMPLATE)
        return template.render(stacks=stacks)

    def describe_stack_resources(self):
        stack_name = self._get_param('StackName')
        stack = cloudformation_backend.get_stack(stack_name)

        template = Template(LIST_STACKS_RESOURCES_RESPONSE)
        return template.render(stack=stack)

    def list_stacks(self):
        stacks = cloudformation_backend.list_stacks()
        template = Template(LIST_STACKS_RESPONSE)
        return template.render(stacks=stacks)

    def get_template(self):
        name_or_stack_id = self.querystring.get('StackName')[0]

        stack = cloudformation_backend.get_stack(name_or_stack_id)
        return stack.template

    # def update_stack(self):
    #     stack_name = self._get_param('StackName')
    #     stack_body = self._get_param('TemplateBody')

    #     stack = cloudformation_backend.update_stack(
    #         name=stack_name,
    #         template=stack_body,
    #     )
    #     stack_body = {
    #         'UpdateStackResponse': {
    #             'UpdateStackResult': {
    #                 'StackId': stack.name,
    #             }
    #         }
    #     }
    #     return json.dumps(stack_body)

    def delete_stack(self):
        name_or_stack_id = self.querystring.get('StackName')[0]

        cloudformation_backend.delete_stack(name_or_stack_id)
        return json.dumps({
            'DeleteStackResponse': {
                'DeleteStackResult': {},
            }
        })


DESCRIBE_STACKS_TEMPLATE = """<DescribeStacksResult>
  <Stacks>
    {% for stack in stacks %}
    <member>
      <StackName>{{ stack.name }}</StackName>
      <StackId>{{ stack.stack_id }}</StackId>
      <CreationTime>2010-07-27T22:28:28Z</CreationTime>
      <StackStatus>CREATE_COMPLETE</StackStatus>
      <DisableRollback>false</DisableRollback>
      <Outputs></Outputs>
    </member>
    {% endfor %}
  </Stacks>
</DescribeStacksResult>"""


LIST_STACKS_RESPONSE = """<ListStacksResponse>
 <ListStacksResult>
  <StackSummaries>
    {% for stack in stacks %}
    <member>
        <StackId>{{ stack.id }}</StackId>
        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
        <StackName>{{ stack.name }}</StackName>
        <CreationTime>2011-05-23T15:47:44Z</CreationTime>
        <TemplateDescription>{{ stack.description }}</TemplateDescription>
    </member>
    {% endfor %}
  </StackSummaries>
 </ListStacksResult>
</ListStacksResponse>"""


LIST_STACKS_RESOURCES_RESPONSE = """<DescribeStackResourcesResult>
  <StackResources>
    {% for resource in stack.stack_resources %}
    <member>
      <StackId>{{ stack.stack_id }}</StackId>
      <StackName>{{ stack.name }}</StackName>
      <LogicalResourceId>{{ resource.logical_resource_id }}</LogicalResourceId>
      <PhysicalResourceId>{{ resource.physical_resource_id }}</PhysicalResourceId>
      <ResourceType>{{ resource.type }}</ResourceType>
      <Timestamp>2010-07-27T22:27:28Z</Timestamp>
      <ResourceStatus>CREATE_COMPLETE</ResourceStatus>
    </member>
    {% endfor %}
  </StackResources>
</DescribeStackResourcesResult>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import CloudFormationResponse

url_bases = [
    "https?://cloudformation.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': CloudFormationResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import uuid


def generate_stack_id(stack_name):
    random_id = uuid.uuid4()
    return "arn:aws:cloudformation:us-east-1:123456789:stack/{0}/{1}".format(stack_name, random_id)

########NEW FILE########
__FILENAME__ = models
import functools
import re

from httpretty import HTTPretty
from .responses import metadata_response
from .utils import convert_regex_to_flask_path


class MockAWS(object):
    nested_count = 0

    def __init__(self, backend):
        self.backend = backend

        if self.__class__.nested_count == 0:
            HTTPretty.reset()

    def __call__(self, func):
        return self.decorate_callable(func)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self):
        self.__class__.nested_count += 1
        self.backend.reset()

        if not HTTPretty.is_enabled():
            HTTPretty.enable()

        for method in HTTPretty.METHODS:
            for key, value in self.backend.urls.iteritems():
                HTTPretty.register_uri(
                    method=method,
                    uri=re.compile(key),
                    body=value,
                )

            # Mock out localhost instance metadata
            HTTPretty.register_uri(
                method=method,
                uri=re.compile('http://169.254.169.254/latest/meta-data/.*'),
                body=metadata_response
            )

    def stop(self):
        self.__class__.nested_count -= 1

        if self.__class__.nested_count < 0:
            raise RuntimeError('Called stop() before start().')

        if self.__class__.nested_count == 0:
            HTTPretty.disable()

    def decorate_callable(self, func):
        def wrapper(*args, **kwargs):
            with self:
                result = func(*args, **kwargs)
            return result
        functools.update_wrapper(wrapper, func)
        wrapper.__wrapped__ = func
        return wrapper


class BaseBackend(object):

    def reset(self):
        self.__dict__ = {}
        self.__init__()

    @property
    def _url_module(self):
        backend_module = self.__class__.__module__
        backend_urls_module_name = backend_module.replace("models", "urls")
        backend_urls_module = __import__(backend_urls_module_name, fromlist=['url_bases', 'url_paths'])
        return backend_urls_module

    @property
    def urls(self):
        """
        A dictionary of the urls to be mocked with this service and the handlers
        that should be called in their place
        """
        url_bases = self._url_module.url_bases
        unformatted_paths = self._url_module.url_paths

        urls = {}
        for url_base in url_bases:
            for url_path, handler in unformatted_paths.iteritems():
                url = url_path.format(url_base)
                urls[url] = handler

        return urls

    @property
    def url_paths(self):
        """
        A dictionary of the paths of the urls to be mocked with this service and
        the handlers that should be called in their place
        """
        unformatted_paths = self._url_module.url_paths

        paths = {}
        for unformatted_path, handler in unformatted_paths.iteritems():
            path = unformatted_path.format("")
            paths[path] = handler

        return paths

    @property
    def url_bases(self):
        """
        A list containing the url_bases extracted from urls.py
        """
        return self._url_module.url_bases

    @property
    def flask_paths(self):
        """
        The url paths that will be used for the flask server
        """
        paths = {}
        for url_path, handler in self.url_paths.iteritems():
            url_path = convert_regex_to_flask_path(url_path)
            paths[url_path] = handler

        return paths

    def decorator(self, func=None):
        if func:
            return MockAWS(self)(func)
        else:
            return MockAWS(self)

########NEW FILE########
__FILENAME__ = responses
import datetime
import json

from urlparse import parse_qs, urlparse

from werkzeug.exceptions import HTTPException
from moto.core.utils import camelcase_to_underscores, method_names_from_class


class BaseResponse(object):

    def dispatch(self, request, full_url, headers):
        querystring = {}

        if hasattr(request, 'body'):
            # Boto
            self.body = request.body
        else:
            # Flask server

            # FIXME: At least in Flask==0.10.1, request.data is an empty string
            # and the information we want is in request.form. Keeping self.body
            # definition for back-compatibility
            self.body = request.data

            querystring = {}
            for key, value in request.form.iteritems():
                querystring[key] = [value, ]

        if not querystring:
            querystring.update(parse_qs(urlparse(full_url).query))
        if not querystring:
            querystring.update(parse_qs(self.body))
        if not querystring:
            querystring.update(headers)

        self.uri = full_url
        self.path = urlparse(full_url).path
        self.querystring = querystring
        self.method = request.method

        self.headers = dict(request.headers)
        self.response_headers = headers
        return self.call_action()

    def call_action(self):
        headers = self.response_headers
        action = self.querystring.get('Action', [""])[0]
        action = camelcase_to_underscores(action)
        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            try:
                response = method()
            except HTTPException as http_error:
                response = http_error.description, dict(status=http_error.code)
            if isinstance(response, basestring):
                return 200, headers, response
            else:
                body, new_headers = response
                status = new_headers.get('status', 200)
                headers.update(new_headers)
                return status, headers, body
        raise NotImplementedError("The {0} action has not been implemented".format(action))

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def _get_multi_param(self, param_prefix):
        if param_prefix.endswith("."):
            prefix = param_prefix
        else:
            prefix = param_prefix + "."
        return [value[0] for key, value in self.querystring.items()
                if key.startswith(prefix)]


def metadata_response(request, full_url, headers):
    """
    Mock response for localhost metadata

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AESDG-chapter-instancedata.html
    """
    parsed_url = urlparse(full_url)
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    credentials = dict(
        AccessKeyId="test-key",
        SecretAccessKey="test-secret-key",
        Token="test-session-token",
        Expiration=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    path = parsed_url.path

    meta_data_prefix = "/latest/meta-data/"
    # Strip prefix if it is there
    if path.startswith(meta_data_prefix):
        path = path[len(meta_data_prefix):]

    if path == '':
        result = 'iam'
    elif path == 'iam':
        result = json.dumps({
            'security-credentials': {
                'default-role': credentials
            }
        })
    elif path == 'iam/security-credentials/':
        result = 'default-role'
    elif path == 'iam/security-credentials/default-role':
        result = json.dumps(credentials)
    return 200, headers, result

########NEW FILE########
__FILENAME__ = utils
import inspect
import random
import re

from flask import request


def camelcase_to_underscores(argument):
    ''' Converts a camelcase param like theNewAttribute to the equivalent
    python underscore variable like the_new_attribute'''
    result = ''
    prev_char_title = True
    for char in argument:
        if char.istitle() and not prev_char_title:
            # Only add underscore if char is capital, not first letter, and prev
            # char wasn't capital
            result += "_"
        prev_char_title = char.istitle()
        if not char.isspace():  # Only add non-whitespace
            result += char.lower()
    return result


def method_names_from_class(clazz):
    return [x[0] for x in inspect.getmembers(clazz, predicate=inspect.ismethod)]


def get_random_hex(length=8):
    chars = range(10) + ['a', 'b', 'c', 'd', 'e', 'f']
    return ''.join(unicode(random.choice(chars)) for x in range(length))


def get_random_message_id():
    return '{0}-{1}-{2}-{3}-{4}'.format(get_random_hex(8), get_random_hex(4), get_random_hex(4), get_random_hex(4), get_random_hex(12))


def convert_regex_to_flask_path(url_path):
    """
    Converts a regex matching url to one that can be used with flask
    """
    for token in ["$"]:
        url_path = url_path.replace(token, "")

    def caller(reg):
        match_name, match_pattern = reg.groups()
        return '<regex("{0}"):{1}>'.format(match_pattern, match_name)

    url_path = re.sub("\(\?P<(.*?)>(.*?)\)", caller, url_path)
    return url_path


class convert_flask_to_httpretty_response(object):
    def __init__(self, callback):
        self.callback = callback

    @property
    def __name__(self):
        # For instance methods, use class and method names. Otherwise
        # use module and method name
        if inspect.ismethod(self.callback):
            outer = self.callback.im_class.__name__
        else:
            outer = self.callback.__module__
        return "{0}.{1}".format(outer, self.callback.__name__)

    def __call__(self, args=None, **kwargs):
        result = self.callback(request, request.url, {})
        # result is a status, headers, response tuple
        status, headers, response = result
        return response, status, headers


def iso_8601_datetime(datetime):
    return datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def rfc_1123_datetime(datetime):
    RFC1123 = '%a, %d %b %Y %H:%M:%S GMT'
    return datetime.strftime(RFC1123)

########NEW FILE########
__FILENAME__ = comparisons
# TODO add tests for all of these
COMPARISON_FUNCS = {
    'EQ': lambda item_value, test_value: item_value == test_value,
    'NE': lambda item_value, test_value: item_value != test_value,
    'LE': lambda item_value, test_value: item_value <= test_value,
    'LT': lambda item_value, test_value: item_value < test_value,
    'GE': lambda item_value, test_value: item_value >= test_value,
    'GT': lambda item_value, test_value: item_value > test_value,
    'NULL': lambda item_value: item_value is None,
    'NOT_NULL': lambda item_value: item_value is not None,
    'CONTAINS': lambda item_value, test_value: test_value in item_value,
    'NOT_CONTAINS': lambda item_value, test_value: test_value not in item_value,
    'BEGINS_WITH': lambda item_value, test_value: item_value.startswith(test_value),
    'IN': lambda item_value, test_value: item_value in test_value,
    'BETWEEN': lambda item_value, lower_test_value, upper_test_value: lower_test_value <= item_value <= upper_test_value,
}


def get_comparison_func(range_comparison):
    return COMPARISON_FUNCS.get(range_comparison)

########NEW FILE########
__FILENAME__ = models
from collections import defaultdict
import datetime
import json

try:
    from collections import OrderedDict
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict


from moto.core import BaseBackend
from .comparisons import get_comparison_func
from .utils import unix_time


class DynamoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_json'):
            return obj.to_json()


def dynamo_json_dump(dynamo_object):
    return json.dumps(dynamo_object, cls=DynamoJsonEncoder)


class DynamoType(object):
    """
    http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DataModel.html#DataModelDataTypes
    """

    def __init__(self, type_as_dict):
        self.type = type_as_dict.keys()[0]
        self.value = type_as_dict.values()[0]

    def __hash__(self):
        return hash((self.type, self.value))

    def __eq__(self, other):
        return (
            self.type == other.type and
            self.value == other.value
        )

    def __repr__(self):
        return "DynamoType: {0}".format(self.to_json())

    def to_json(self):
        return {self.type: self.value}

    def compare(self, range_comparison, range_objs):
        """
        Compares this type against comparison filters
        """
        range_values = [obj.value for obj in range_objs]
        comparison_func = get_comparison_func(range_comparison)
        return comparison_func(self.value, *range_values)


class Item(object):
    def __init__(self, hash_key, hash_key_type, range_key, range_key_type, attrs):
        self.hash_key = hash_key
        self.hash_key_type = hash_key_type
        self.range_key = range_key
        self.range_key_type = range_key_type

        self.attrs = {}
        for key, value in attrs.iteritems():
            self.attrs[key] = DynamoType(value)

    def __repr__(self):
        return "Item: {0}".format(self.to_json())

    def to_json(self):
        attributes = {}
        for attribute_key, attribute in self.attrs.iteritems():
            attributes[attribute_key] = attribute.value

        return {
            "Attributes": attributes
        }

    def describe_attrs(self, attributes):
        if attributes:
            included = {}
            for key, value in self.attrs.iteritems():
                if key in attributes:
                    included[key] = value
        else:
            included = self.attrs
        return {
            "Item": included
        }


class Table(object):

    def __init__(self, name, hash_key_attr, hash_key_type,
                 range_key_attr=None, range_key_type=None, read_capacity=None,
                 write_capacity=None):
        self.name = name
        self.hash_key_attr = hash_key_attr
        self.hash_key_type = hash_key_type
        self.range_key_attr = range_key_attr
        self.range_key_type = range_key_type
        self.read_capacity = read_capacity
        self.write_capacity = write_capacity
        self.created_at = datetime.datetime.now()
        self.items = defaultdict(dict)

    @property
    def has_range_key(self):
        return self.range_key_attr is not None

    @property
    def describe(self):
        results = {
            "Table": {
                "CreationDateTime": unix_time(self.created_at),
                "KeySchema": {
                    "HashKeyElement": {
                        "AttributeName": self.hash_key_attr,
                        "AttributeType": self.hash_key_type
                    },
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": self.read_capacity,
                    "WriteCapacityUnits": self.write_capacity
                },
                "TableName": self.name,
                "TableStatus": "ACTIVE",
                "ItemCount": len(self),
                "TableSizeBytes": 0,
            }
        }
        if self.has_range_key:
            results["Table"]["KeySchema"]["RangeKeyElement"] = {
                "AttributeName": self.range_key_attr,
                "AttributeType": self.range_key_type
            }
        return results

    def __len__(self):
        count = 0
        for key, value in self.items.iteritems():
            if self.has_range_key:
                count += len(value)
            else:
                count += 1
        return count

    def __nonzero__(self):
        return True

    def put_item(self, item_attrs):
        hash_value = DynamoType(item_attrs.get(self.hash_key_attr))
        if self.has_range_key:
            range_value = DynamoType(item_attrs.get(self.range_key_attr))
        else:
            range_value = None

        item = Item(hash_value, self.hash_key_type, range_value, self.range_key_type, item_attrs)

        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item
        return item

    def get_item(self, hash_key, range_key):
        if self.has_range_key and not range_key:
            raise ValueError("Table has a range key, but no range key was passed into get_item")
        try:
            if range_key:
                return self.items[hash_key][range_key]
            else:
                return self.items[hash_key]
        except KeyError:
            return None

    def query(self, hash_key, range_comparison, range_objs):
        results = []
        last_page = True  # Once pagination is implemented, change this

        if self.range_key_attr:
            possible_results = self.items[hash_key].values()
        else:
            possible_results = list(self.all_items())

        if range_comparison:
            for result in possible_results:
                if result.range_key.compare(range_comparison, range_objs):
                    results.append(result)
        else:
            # If we're not filtering on range key, return all values
            results = possible_results
        return results, last_page

    def all_items(self):
        for hash_set in self.items.values():
            if self.range_key_attr:
                for item in hash_set.values():
                    yield item
            else:
                yield hash_set

    def scan(self, filters):
        results = []
        scanned_count = 0
        last_page = True  # Once pagination is implemented, change this

        for result in self.all_items():
            scanned_count += 1
            passes_all_conditions = True
            for attribute_name, (comparison_operator, comparison_objs) in filters.iteritems():
                attribute = result.attrs.get(attribute_name)

                if attribute:
                    # Attribute found
                    if not attribute.compare(comparison_operator, comparison_objs):
                        passes_all_conditions = False
                        break
                elif comparison_operator == 'NULL':
                    # Comparison is NULL and we don't have the attribute
                    continue
                else:
                    # No attribute found and comparison is no NULL. This item fails
                    passes_all_conditions = False
                    break

            if passes_all_conditions:
                results.append(result)

        return results, scanned_count, last_page

    def delete_item(self, hash_key, range_key):
        try:
            if range_key:
                return self.items[hash_key].pop(range_key)
            else:
                return self.items.pop(hash_key)
        except KeyError:
            return None


class DynamoDBBackend(BaseBackend):

    def __init__(self):
        self.tables = OrderedDict()

    def create_table(self, name, **params):
        table = Table(name, **params)
        self.tables[name] = table
        return table

    def delete_table(self, name):
        return self.tables.pop(name, None)

    def update_table_throughput(self, name, new_read_units, new_write_units):
        table = self.tables[name]
        table.read_capacity = new_read_units
        table.write_capacity = new_write_units
        return table

    def put_item(self, table_name, item_attrs):
        table = self.tables.get(table_name)
        if not table:
            return None

        return table.put_item(item_attrs)

    def get_item(self, table_name, hash_key_dict, range_key_dict):
        table = self.tables.get(table_name)
        if not table:
            return None

        hash_key = DynamoType(hash_key_dict)
        range_key = DynamoType(range_key_dict) if range_key_dict else None

        return table.get_item(hash_key, range_key)

    def query(self, table_name, hash_key_dict, range_comparison, range_value_dicts):
        table = self.tables.get(table_name)
        if not table:
            return None, None

        hash_key = DynamoType(hash_key_dict)
        range_values = [DynamoType(range_value) for range_value in range_value_dicts]

        return table.query(hash_key, range_comparison, range_values)

    def scan(self, table_name, filters):
        table = self.tables.get(table_name)
        if not table:
            return None, None, None

        scan_filters = {}
        for key, (comparison_operator, comparison_values) in filters.iteritems():
            dynamo_types = [DynamoType(value) for value in comparison_values]
            scan_filters[key] = (comparison_operator, dynamo_types)

        return table.scan(scan_filters)

    def delete_item(self, table_name, hash_key_dict, range_key_dict):
        table = self.tables.get(table_name)
        if not table:
            return None

        hash_key = DynamoType(hash_key_dict)
        range_key = DynamoType(range_key_dict) if range_key_dict else None

        return table.delete_item(hash_key, range_key)


dynamodb_backend = DynamoDBBackend()

########NEW FILE########
__FILENAME__ = responses
import json

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import dynamodb_backend, dynamo_json_dump


GET_SESSION_TOKEN_RESULT = """
<GetSessionTokenResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
 <GetSessionTokenResult>
 <Credentials>
 <SessionToken>
 AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/L
 To6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3z
 rkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtp
 Z3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE
 </SessionToken>
 <SecretAccessKey>
 wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
 </SecretAccessKey>
 <Expiration>2011-07-11T19:55:29.611Z</Expiration>
 <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
 </Credentials>
 </GetSessionTokenResult>
 <ResponseMetadata>
 <RequestId>58c5dbae-abef-11e0-8cfe-09039844ac7d</RequestId>
 </ResponseMetadata>
</GetSessionTokenResponse>"""


def sts_handler():
    return GET_SESSION_TOKEN_RESULT


class DynamoHandler(BaseResponse):

    def get_endpoint_name(self, headers):
        """Parses request headers and extracts part od the X-Amz-Target
        that corresponds to a method of DynamoHandler

        ie: X-Amz-Target: DynamoDB_20111205.ListTables -> ListTables
        """
        # Headers are case-insensitive. Probably a better way to do this.
        match = headers.get('x-amz-target') or headers.get('X-Amz-Target')
        if match:
            return match.split(".")[1]

    def error(self, type_, status=400):
        return status, self.response_headers, dynamo_json_dump({'__type': type_})

    def call_action(self):
        if 'GetSessionToken' in self.body:
            return 200, self.response_headers, sts_handler()

        self.body = json.loads(self.body or '{}')
        endpoint = self.get_endpoint_name(self.headers)
        if endpoint:
            endpoint = camelcase_to_underscores(endpoint)
            response = getattr(self, endpoint)()
            if isinstance(response, basestring):
                return 200, self.response_headers, response

            else:
                status_code, new_headers, response_content = response
                self.response_headers.update(new_headers)
                return status_code, self.response_headers, response_content
        else:
            return 404, self.response_headers, ""

    def list_tables(self):
        body = self.body
        limit = body.get('Limit')
        if body.get("ExclusiveStartTableName"):
            last = body.get("ExclusiveStartTableName")
            start = dynamodb_backend.tables.keys().index(last) + 1
        else:
            start = 0
        all_tables = dynamodb_backend.tables.keys()
        if limit:
            tables = all_tables[start:start + limit]
        else:
            tables = all_tables[start:]
        response = {"TableNames": tables}
        if limit and len(all_tables) > start + limit:
            response["LastEvaluatedTableName"] = tables[-1]
        return dynamo_json_dump(response)

    def create_table(self):
        body = self.body
        name = body['TableName']

        key_schema = body['KeySchema']
        hash_hey = key_schema['HashKeyElement']
        hash_key_attr = hash_hey['AttributeName']
        hash_key_type = hash_hey['AttributeType']

        range_hey = key_schema.get('RangeKeyElement', {})
        range_key_attr = range_hey.get('AttributeName')
        range_key_type = range_hey.get('AttributeType')

        throughput = body["ProvisionedThroughput"]
        read_units = throughput["ReadCapacityUnits"]
        write_units = throughput["WriteCapacityUnits"]

        table = dynamodb_backend.create_table(
            name,
            hash_key_attr=hash_key_attr,
            hash_key_type=hash_key_type,
            range_key_attr=range_key_attr,
            range_key_type=range_key_type,
            read_capacity=int(read_units),
            write_capacity=int(write_units),
        )
        return dynamo_json_dump(table.describe)

    def delete_table(self):
        name = self.body['TableName']
        table = dynamodb_backend.delete_table(name)
        if table:
            return dynamo_json_dump(table.describe)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

    def update_table(self):
        name = self.body['TableName']
        throughput = self.body["ProvisionedThroughput"]
        new_read_units = throughput["ReadCapacityUnits"]
        new_write_units = throughput["WriteCapacityUnits"]
        table = dynamodb_backend.update_table_throughput(name, new_read_units, new_write_units)
        return dynamo_json_dump(table.describe)

    def describe_table(self):
        name = self.body['TableName']
        try:
            table = dynamodb_backend.tables[name]
        except KeyError:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)
        return dynamo_json_dump(table.describe)

    def put_item(self):
        name = self.body['TableName']
        item = self.body['Item']
        result = dynamodb_backend.put_item(name, item)
        if result:
            item_dict = result.to_json()
            item_dict['ConsumedCapacityUnits'] = 1
            return dynamo_json_dump(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

    def batch_write_item(self):
        table_batches = self.body['RequestItems']

        for table_name, table_requests in table_batches.iteritems():
            for table_request in table_requests:
                request_type = table_request.keys()[0]
                request = table_request.values()[0]

                if request_type == 'PutRequest':
                    item = request['Item']
                    dynamodb_backend.put_item(table_name, item)
                elif request_type == 'DeleteRequest':
                    key = request['Key']
                    hash_key = key['HashKeyElement']
                    range_key = key.get('RangeKeyElement')
                    item = dynamodb_backend.delete_item(table_name, hash_key, range_key)

        response = {
            "Responses": {
                "Thread": {
                    "ConsumedCapacityUnits": 1.0
                },
                "Reply": {
                    "ConsumedCapacityUnits": 1.0
                }
            },
            "UnprocessedItems": {}
        }

        return dynamo_json_dump(response)

    def get_item(self):
        name = self.body['TableName']
        key = self.body['Key']
        hash_key = key['HashKeyElement']
        range_key = key.get('RangeKeyElement')
        attrs_to_get = self.body.get('AttributesToGet')
        try:
            item = dynamodb_backend.get_item(name, hash_key, range_key)
        except ValueError:
            er = 'com.amazon.coral.validate#ValidationException'
            return self.error(er, status=400)
        if item:
            item_dict = item.describe_attrs(attrs_to_get)
            item_dict['ConsumedCapacityUnits'] = 0.5
            return dynamo_json_dump(item_dict)
        else:
            # Item not found
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, status=404)

    def batch_get_item(self):
        table_batches = self.body['RequestItems']

        results = {
            "Responses": {
                "UnprocessedKeys": {}
            }
        }

        for table_name, table_request in table_batches.iteritems():
            items = []
            keys = table_request['Keys']
            attributes_to_get = table_request.get('AttributesToGet')
            for key in keys:
                hash_key = key["HashKeyElement"]
                range_key = key.get("RangeKeyElement")
                item = dynamodb_backend.get_item(table_name, hash_key, range_key)
                if item:
                    item_describe = item.describe_attrs(attributes_to_get)
                    items.append(item_describe)
            results["Responses"][table_name] = {"Items": items, "ConsumedCapacityUnits": 1}
        return dynamo_json_dump(results)

    def query(self):
        name = self.body['TableName']
        hash_key = self.body['HashKeyValue']
        range_condition = self.body.get('RangeKeyCondition')
        if range_condition:
            range_comparison = range_condition['ComparisonOperator']
            range_values = range_condition['AttributeValueList']
        else:
            range_comparison = None
            range_values = []

        items, last_page = dynamodb_backend.query(name, hash_key, range_comparison, range_values)

        if items is None:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacityUnits": 1,
        }

        # Implement this when we do pagination
        # if not last_page:
        #     result["LastEvaluatedKey"] = {
        #         "HashKeyElement": items[-1].hash_key,
        #         "RangeKeyElement": items[-1].range_key,
        #     }
        return dynamo_json_dump(result)

    def scan(self):
        name = self.body['TableName']

        filters = {}
        scan_filters = self.body.get('ScanFilter', {})
        for attribute_name, scan_filter in scan_filters.iteritems():
            # Keys are attribute names. Values are tuples of (comparison, comparison_value)
            comparison_operator = scan_filter["ComparisonOperator"]
            comparison_values = scan_filter.get("AttributeValueList", [])
            filters[attribute_name] = (comparison_operator, comparison_values)

        items, scanned_count, last_page = dynamodb_backend.scan(name, filters)

        if items is None:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacityUnits": 1,
            "ScannedCount": scanned_count
        }

        # Implement this when we do pagination
        # if not last_page:
        #     result["LastEvaluatedKey"] = {
        #         "HashKeyElement": items[-1].hash_key,
        #         "RangeKeyElement": items[-1].range_key,
        #     }
        return dynamo_json_dump(result)

    def delete_item(self):
        name = self.body['TableName']
        key = self.body['Key']
        hash_key = key['HashKeyElement']
        range_key = key.get('RangeKeyElement')
        return_values = self.body.get('ReturnValues', '')
        item = dynamodb_backend.delete_item(name, hash_key, range_key)
        if item:
            if return_values == 'ALL_OLD':
                item_dict = item.to_json()
            else:
                item_dict = {'Attributes': []}
            item_dict['ConsumedCapacityUnits'] = 0.5
            return dynamo_json_dump(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

########NEW FILE########
__FILENAME__ = urls
from .responses import DynamoHandler

url_bases = [
    "https?://dynamodb.(.+).amazonaws.com",
    "https?://sts.amazonaws.com",
]

url_paths = {
    "{0}/": DynamoHandler().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import calendar


def unix_time(dt):
    return calendar.timegm(dt.timetuple())

########NEW FILE########
__FILENAME__ = comparisons
# TODO add tests for all of these
COMPARISON_FUNCS = {
    'EQ': lambda item_value, test_value: item_value == test_value,
    'NE': lambda item_value, test_value: item_value != test_value,
    'LE': lambda item_value, test_value: item_value <= test_value,
    'LT': lambda item_value, test_value: item_value < test_value,
    'GE': lambda item_value, test_value: item_value >= test_value,
    'GT': lambda item_value, test_value: item_value > test_value,
    'NULL': lambda item_value: item_value is None,
    'NOT_NULL': lambda item_value: item_value is not None,
    'CONTAINS': lambda item_value, test_value: test_value in item_value,
    'NOT_CONTAINS': lambda item_value, test_value: test_value not in item_value,
    'BEGINS_WITH': lambda item_value, test_value: item_value.startswith(test_value),
    'IN': lambda item_value, test_value: item_value in test_value,
    'BETWEEN': lambda item_value, lower_test_value, upper_test_value: lower_test_value <= item_value <= upper_test_value,
}


def get_comparison_func(range_comparison):
    return COMPARISON_FUNCS.get(range_comparison)

########NEW FILE########
__FILENAME__ = models
from collections import defaultdict
import datetime
import json

try:
        from collections import OrderedDict
except ImportError:
        # python 2.6 or earlier, use backport
        from ordereddict import OrderedDict


from moto.core import BaseBackend
from .comparisons import get_comparison_func
from .utils import unix_time


class DynamoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_json'):
            return obj.to_json()


def dynamo_json_dump(dynamo_object):
    return json.dumps(dynamo_object, cls=DynamoJsonEncoder)


class DynamoType(object):
    """
    http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DataModel.html#DataModelDataTypes
    """

    def __init__(self, type_as_dict):
        self.type = type_as_dict.keys()[0]
        self.value = type_as_dict.values()[0]

    def __hash__(self):
        return hash((self.type, self.value))

    def __eq__(self, other):
        return (
            self.type == other.type and
            self.value == other.value
        )

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __repr__(self):
        return "DynamoType: {0}".format(self.to_json())

    def to_json(self):
        return {self.type: self.value}

    def compare(self, range_comparison, range_objs):
        """
        Compares this type against comparison filters
        """
        range_values = [obj.value for obj in range_objs]
        comparison_func = get_comparison_func(range_comparison)
        return comparison_func(self.value, *range_values)

class Item(object):
    def __init__(self, hash_key, hash_key_type, range_key, range_key_type, attrs):
        self.hash_key = hash_key
        self.hash_key_type = hash_key_type
        self.range_key = range_key
        self.range_key_type = range_key_type

        self.attrs = {}
        for key, value in attrs.iteritems():
            self.attrs[key] = DynamoType(value)

    def __repr__(self):
        return "Item: {0}".format(self.to_json())

    def to_json(self):
        attributes = {}
        for attribute_key, attribute in self.attrs.iteritems():
            attributes[attribute_key] = attribute.value

        return {
            "Attributes": attributes
        }

    def describe_attrs(self, attributes):
        if attributes:
            included = {}
            for key, value in self.attrs.iteritems():
                if key in attributes:
                    included[key] = value
        else:
            included = self.attrs
        return {
            "Item": included
        }

class Table(object):

    def __init__(self, table_name, schema=None, attr = None, throughput=None, indexes=None):
        self.name = table_name
        self.attr = attr
        self.schema = schema
        self.range_key_attr = None
        self.hash_key_attr = None
        self.range_key_type = None
        self.hash_key_type = None
        for elem in schema:
            if elem["KeyType"] == "HASH":
                self.hash_key_attr = elem["AttributeName"]
                self.hash_key_type = elem["KeyType"]
            else:
                self.range_key_attr = elem["AttributeName"]
                self.range_key_type = elem["KeyType"]
        if throughput is None:
             self.throughput = {u'WriteCapacityUnits': 10, u'ReadCapacityUnits': 10}
        else:
            self.throughput = throughput
        self.throughput["NumberOfDecreasesToday"] = 0
        self.indexes = indexes
        self.created_at = datetime.datetime.now()
        self.items = defaultdict(dict)
        
    @property
    def describe(self):
        results = {
        'Table': {
            'AttributeDefinitions': self.attr,
            'ProvisionedThroughput': self.throughput, 
            'TableSizeBytes': 0, 
            'TableName': self.name, 
            'TableStatus': 'ACTIVE', 
            'KeySchema': self.schema, 
            'ItemCount': len(self), 
            'CreationDateTime': unix_time(self.created_at)
            }
        }
        return results
    
    def __len__(self):
        count = 0
        for key, value in self.items.iteritems():
            if self.has_range_key:
                count += len(value)
            else:
                count += 1
        return count
    
    def put_item(self, item_attrs):
        hash_value = DynamoType(item_attrs.get(self.hash_key_attr))
        if self.has_range_key:
            range_value = DynamoType(item_attrs.get(self.range_key_attr))
        else:
            range_value = None

        item = Item(hash_value, self.hash_key_type, range_value, self.range_key_type, item_attrs)

        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item
        return item
    
    def __nonzero__(self):
        return True
    
    @property
    def has_range_key(self):
        return self.range_key_attr is not None
    
    def get_item(self, hash_key, range_key):
        if self.has_range_key and not range_key:
            raise ValueError("Table has a range key, but no range key was passed into get_item")
        try:
            if range_key:
                return self.items[hash_key][range_key]
            else:
                return self.items[hash_key]
        except KeyError:
            return None
        
    def delete_item(self, hash_key, range_key):
        try:
            if range_key:
                return self.items[hash_key].pop(range_key)
            else:
                return self.items.pop(hash_key)
        except KeyError:
            return None
        
    def query(self, hash_key, range_comparison, range_objs):
        results = []
        last_page = True  # Once pagination is implemented, change this

        possible_results =  [ item for item in list(self.all_items()) if item.hash_key == hash_key] 
        if range_comparison:
            for result in possible_results:
                if result.range_key.compare(range_comparison, range_objs):
                    results.append(result)
        else:
            # If we're not filtering on range key, return all values
            results = possible_results

        results.sort(key=lambda item: item.range_key)
        return results, last_page

    def all_items(self):
        for hash_set in self.items.values():
            if self.range_key_attr:
                for item in hash_set.values():
                    yield item
            else:
                yield hash_set
                
    def scan(self, filters):
        results = []
        scanned_count = 0
        last_page = True  # Once pagination is implemented, change this

        for result in self.all_items():
            scanned_count += 1
            passes_all_conditions = True
            for attribute_name, (comparison_operator, comparison_objs) in filters.iteritems():
                attribute = result.attrs.get(attribute_name)

                if attribute:
                    # Attribute found
                    if not attribute.compare(comparison_operator, comparison_objs):
                        passes_all_conditions = False
                        break
                elif comparison_operator == 'NULL':
                    # Comparison is NULL and we don't have the attribute
                    continue
                else:
                    # No attribute found and comparison is no NULL. This item fails
                    passes_all_conditions = False
                    break

            if passes_all_conditions:
                results.append(result)
        return results, scanned_count, last_page
    

class DynamoDBBackend(BaseBackend):

    def __init__(self):
        self.tables = OrderedDict()

    def create_table(self, name, **params):
        table = Table(name, **params)
        self.tables[name] = table
        return table

    def delete_table(self, name):
        return self.tables.pop(name, None)

    def update_table_throughput(self, name, throughput):
        table = self.tables[name]
        table.throughput = throughput
        return table

    def put_item(self, table_name, item_attrs):
        table = self.tables.get(table_name)
        if not table:
            return None
        return table.put_item(item_attrs)
    
    def get_table_keys_name(self, table_name):
        table = self.tables.get(table_name)
        if not table:
            return None, None
        else:
            return table.hash_key_attr, table.range_key_attr
         
    def get_keys_value(self, table, keys):
        if not table.hash_key_attr in keys or (table.has_range_key and not table.range_key_attr in keys):
            raise ValueError("Table has a range key, but no range key was passed into get_item")        
        hash_key = DynamoType(keys[table.hash_key_attr])    
        range_key = DynamoType(keys[table.range_key_attr]) if table.has_range_key else None
        return hash_key,range_key

    def get_item(self, table_name, keys):
        table = self.tables.get(table_name)
        if not table:
            return None
        hash_key,range_key = self.get_keys_value(table,keys)
        return table.get_item(hash_key, range_key)

    def query(self, table_name, hash_key_dict, range_comparison, range_value_dicts):
        table = self.tables.get(table_name)
        if not table:
            return None, None

        hash_key = DynamoType(hash_key_dict)
        range_values = [DynamoType(range_value) for range_value in range_value_dicts]

        return table.query(hash_key, range_comparison, range_values)
    
    def scan(self, table_name, filters):
        table = self.tables.get(table_name)
        if not table:
            return None, None, None

        scan_filters = {}
        for key, (comparison_operator, comparison_values) in filters.iteritems():
            dynamo_types = [DynamoType(value) for value in comparison_values]
            scan_filters[key] = (comparison_operator, dynamo_types)

        return table.scan(scan_filters)
    
    def delete_item(self, table_name, keys):
        table = self.tables.get(table_name)
        if not table:
            return None
        hash_key, range_key = self.get_keys_value(table, keys)
        return table.delete_item(hash_key, range_key)


dynamodb_backend2 = DynamoDBBackend()

########NEW FILE########
__FILENAME__ = responses
import json

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import dynamodb_backend2, dynamo_json_dump


GET_SESSION_TOKEN_RESULT = """
<GetSessionTokenResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
 <GetSessionTokenResult>
 <Credentials>
 <SessionToken>
 AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/L
 To6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3z
 rkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtp
 Z3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE
 </SessionToken>
 <SecretAccessKey>
 wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
 </SecretAccessKey>
 <Expiration>2011-07-11T19:55:29.611Z</Expiration>
 <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
 </Credentials>
 </GetSessionTokenResult>
 <ResponseMetadata>
 <RequestId>58c5dbae-abef-11e0-8cfe-09039844ac7d</RequestId>
 </ResponseMetadata>
</GetSessionTokenResponse>"""


def sts_handler():
    return GET_SESSION_TOKEN_RESULT


class DynamoHandler(BaseResponse):

    def get_endpoint_name(self, headers):
        """Parses request headers and extracts part od the X-Amz-Target
        that corresponds to a method of DynamoHandler

        ie: X-Amz-Target: DynamoDB_20111205.ListTables -> ListTables
        """
        # Headers are case-insensitive. Probably a better way to do this.
        match = headers.get('x-amz-target') or headers.get('X-Amz-Target')
        if match:
            return match.split(".")[1]

    def error(self, type_, status=400):
        return status, self.response_headers, dynamo_json_dump({'__type': type_})

    def call_action(self):
        if 'GetSessionToken' in self.body:
            return 200, self.response_headers, sts_handler()

        self.body = json.loads(self.body or '{}')
        endpoint = self.get_endpoint_name(self.headers)
        if endpoint:
            endpoint = camelcase_to_underscores(endpoint)
            response = getattr(self, endpoint)()
            if isinstance(response, basestring):
                return 200, self.response_headers, response

            else:
                status_code, new_headers, response_content = response
                self.response_headers.update(new_headers)
                return status_code, self.response_headers, response_content
        else:
            return 404, self.response_headers, ""

    def list_tables(self):
        body = self.body
        limit = body.get('Limit')
        if body.get("ExclusiveStartTableName"):
            last = body.get("ExclusiveStartTableName")
            start = dynamodb_backend2.tables.keys().index(last) + 1
        else:
            start = 0
        all_tables = dynamodb_backend2.tables.keys()
        if limit:
            tables = all_tables[start:start + limit]
        else:
            tables = all_tables[start:]
        response = {"TableNames": tables}
        if limit and len(all_tables) > start + limit:
            response["LastEvaluatedTableName"] = tables[-1]
        return dynamo_json_dump(response)

    def create_table(self):
        body = self.body
        #get the table name
        table_name = body['TableName']
        #get the throughput
        throughput = body["ProvisionedThroughput"]        
        #getting the schema
        key_schema = body['KeySchema']
        #getting attribute definition
        attr = body["AttributeDefinitions"]
        #getting the indexes
        table = dynamodb_backend2.create_table(table_name, 
                   schema = key_schema,           
                   throughput = throughput, 
                   attr = attr)
        return dynamo_json_dump(table.describe)        

    def delete_table(self):
        name = self.body['TableName']
        table = dynamodb_backend2.delete_table(name)
        if table is not None:
            return dynamo_json_dump(table.describe)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

    def update_table(self):
        name = self.body['TableName']
        throughput = self.body["ProvisionedThroughput"]
        table = dynamodb_backend2.update_table_throughput(name, throughput)
        return dynamo_json_dump(table.describe)

    def describe_table(self):
        name = self.body['TableName']
        try:
            table = dynamodb_backend2.tables[name]
        except KeyError:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)
        return dynamo_json_dump(table.describe)

    def put_item(self):
        name = self.body['TableName']
        item = self.body['Item']
        result = dynamodb_backend2.put_item(name, item)
        
        if result:
            item_dict = result.to_json()
            item_dict['ConsumedCapacityUnits'] = 1
            return dynamo_json_dump(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

    def batch_write_item(self):
        table_batches = self.body['RequestItems']

        for table_name, table_requests in table_batches.iteritems():
            for table_request in table_requests:
                request_type = table_request.keys()[0]
                request = table_request.values()[0]
                if request_type == 'PutRequest':
                    item = request['Item']
                    dynamodb_backend2.put_item(table_name, item)
                elif request_type == 'DeleteRequest':
                    keys = request['Key']
                    item = dynamodb_backend2.delete_item(table_name, keys)

        response = {
            "Responses": {
                "Thread": {
                    "ConsumedCapacityUnits": 1.0
                },
                "Reply": {
                    "ConsumedCapacityUnits": 1.0
                }
            },
            "UnprocessedItems": {}
        }

        return dynamo_json_dump(response)
    def get_item(self):
        name = self.body['TableName']
        key = self.body['Key']
        try:
            item = dynamodb_backend2.get_item(name, key)
        except ValueError:
            er = 'com.amazon.coral.validate#ValidationException'
            return self.error(er, status=400)
        if item:
            item_dict = item.describe_attrs(attributes = None)
            item_dict['ConsumedCapacityUnits'] = 0.5
            return dynamo_json_dump(item_dict)
        else:
            # Item not found
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, status=404)

    def batch_get_item(self):
        table_batches = self.body['RequestItems']

        results = { 
            "ConsumedCapacity":[],
            "Responses": {                
            },
            "UnprocessedKeys": {
            }
        }

        for table_name, table_request in table_batches.iteritems():
            items = []
            keys = table_request['Keys']
            attributes_to_get = table_request.get('AttributesToGet')
            results["Responses"][table_name]=[]
            for key in keys:
                item = dynamodb_backend2.get_item(table_name, key)
                if item:
                    item_describe = item.describe_attrs(attributes_to_get)
                    results["Responses"][table_name].append(item_describe["Item"])

            results["ConsumedCapacity"].append({
                "CapacityUnits": len(keys),
                "TableName": table_name
            })
        return dynamo_json_dump(results)

    def query(self):
        name = self.body['TableName']
        keys = self.body['KeyConditions']
        hash_key_name, range_key_name = dynamodb_backend2.get_table_keys_name(name)
        if hash_key_name is None:
            er = "'com.amazonaws.dynamodb.v20120810#ResourceNotFoundException"  
            return self.error(er)
        hash_key = keys[hash_key_name]['AttributeValueList'][0]
        if len(keys) == 1:
            range_comparison = None
            range_values = []
        else:
            if range_key_name == None:
                er = "com.amazon.coral.validate#ValidationException"  
                return self.error(er)
            else:
                range_condition = keys[range_key_name]
                if range_condition:
                    range_comparison = range_condition['ComparisonOperator']
                    range_values = range_condition['AttributeValueList']
                else:
                    range_comparison = None
                    range_values = []
        items, last_page = dynamodb_backend2.query(name, hash_key, range_comparison, range_values)
        if items is None:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er) 

        limit = self.body.get("Limit")
        if limit:
            items = items[:limit]

        reversed = self.body.get("ScanIndexForward")
        if reversed != False:
            items.reverse()

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacityUnits": 1,
        }

        # Implement this when we do pagination
        # if not last_page:
        #     result["LastEvaluatedKey"] = {
        #         "HashKeyElement": items[-1].hash_key,
        #         "RangeKeyElement": items[-1].range_key,
        #     }
        return dynamo_json_dump(result)

    def scan(self):
        name = self.body['TableName']

        filters = {}
        scan_filters = self.body.get('ScanFilter', {})
        for attribute_name, scan_filter in scan_filters.iteritems():
            # Keys are attribute names. Values are tuples of (comparison, comparison_value)
            comparison_operator = scan_filter["ComparisonOperator"]
            comparison_values = scan_filter.get("AttributeValueList", [])
            filters[attribute_name] = (comparison_operator, comparison_values)

        items, scanned_count, last_page = dynamodb_backend2.scan(name, filters)

        if items is None:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

        limit = self.body.get("Limit")
        if limit:
            items = items[:limit]

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacityUnits": 1,
            "ScannedCount": scanned_count
        }

        # Implement this when we do pagination
        # if not last_page:
        #     result["LastEvaluatedKey"] = {
        #         "HashKeyElement": items[-1].hash_key,
        #         "RangeKeyElement": items[-1].range_key,
        #     }
        return dynamo_json_dump(result)

    def delete_item(self):
        name = self.body['TableName']
        keys = self.body['Key']
        return_values = self.body.get('ReturnValues', '')
        item = dynamodb_backend2.delete_item(name, keys)
        if item:
            if return_values == 'ALL_OLD':
                item_dict = item.to_json()
            else:
                item_dict = {'Attributes': []}
            item_dict['ConsumedCapacityUnits'] = 0.5
            return dynamo_json_dump(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20120810#ConditionalCheckFailedException'
            return self.error(er)

########NEW FILE########
__FILENAME__ = urls
from .responses import DynamoHandler

url_bases = [
    "https?://dynamodb.(.+).amazonaws.com",
    "https?://sts.amazonaws.com",
]

url_paths = {
    "{0}/": DynamoHandler().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import calendar


def unix_time(dt):
    return calendar.timegm(dt.timetuple())

########NEW FILE########
__FILENAME__ = exceptions
from werkzeug.exceptions import BadRequest
from jinja2 import Template

class InvalidIdError(RuntimeError):
    def __init__(self, id_value):
        super(InvalidIdError, self).__init__()
        self.id = id_value


class EC2ClientError(BadRequest):
    def __init__(self, code, message):
        super(EC2ClientError, self).__init__()
        self.description = ERROR_RESPONSE_TEMPLATE.render(
            code=code, message=message)


class DependencyViolationError(EC2ClientError):
    def __init__(self, message):
        super(DependencyViolationError, self).__init__(
            "DependencyViolation", message)


class InvalidDHCPOptionsIdError(EC2ClientError):
    def __init__(self, dhcp_options_id):
        super(InvalidDHCPOptionsIdError, self).__init__(
            "InvalidDhcpOptionID.NotFound",
            "DhcpOptionID {0} does not exist."
            .format(dhcp_options_id))


class InvalidVPCIdError(EC2ClientError):
    def __init__(self, vpc_id):
        super(InvalidVPCIdError, self).__init__(
            "InvalidVpcID.NotFound",
            "VpcID {0} does not exist."
            .format(vpc_id))


class InvalidParameterValueError(EC2ClientError):
    def __init__(self, parameter_value):
            super(InvalidParameterValueError, self).__init__(
                "InvalidParameterValue",
                "Value ({0}) for parameter value is invalid. Invalid DHCP option value.".format(
                    parameter_value))




ERROR_RESPONSE = u"""<?xml version="1.0" encoding="UTF-8"?>
  <Response>
    <Errors>
      <Error>
        <Code>{{code}}</Code>
        <Message>{{message}}</Message>
      </Error>
    </Errors>
  <RequestID>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestID>
</Response>
"""
ERROR_RESPONSE_TEMPLATE = Template(ERROR_RESPONSE)

########NEW FILE########
__FILENAME__ = models
import copy
import itertools
from collections import defaultdict

from boto.ec2.instance import Instance as BotoInstance, Reservation

from moto.core import BaseBackend
from .exceptions import (
    InvalidIdError,
    DependencyViolationError,
    InvalidDHCPOptionsIdError
)
from .utils import (
    random_ami_id,
    random_dhcp_option_id,
    random_eip_allocation_id,
    random_eip_association_id,
    random_gateway_id,
    random_instance_id,
    random_ip,
    random_key_pair,
    random_reservation_id,
    random_route_table_id,
    random_security_group_id,
    random_snapshot_id,
    random_spot_request_id,
    random_subnet_id,
    random_volume_id,
    random_vpc_id,
)


class InstanceState(object):
    def __init__(self, name='pending', code=0):
        self.name = name
        self.code = code


class TaggedEC2Instance(object):
    def get_tags(self, *args, **kwargs):
        tags = ec2_backend.describe_tags(self.id)
        return tags


class Instance(BotoInstance, TaggedEC2Instance):
    def __init__(self, image_id, user_data, security_groups, **kwargs):
        super(Instance, self).__init__()
        self.id = random_instance_id()
        self.image_id = image_id
        self._state = InstanceState("running", 16)
        self.user_data = user_data
        self.security_groups = security_groups
        self.instance_type = kwargs.get("instance_type", "m1.small")
        self.subnet_id = kwargs.get("subnet_id")
        self.key_name = kwargs.get("key_name")

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        security_group_ids = properties.get('SecurityGroups', [])
        group_names = [ec2_backend.get_security_group_from_id(group_id).name for group_id in security_group_ids]

        reservation = ec2_backend.add_instances(
            image_id=properties['ImageId'],
            user_data=properties.get('UserData'),
            count=1,
            security_group_names=group_names,
            instance_type=properties.get("InstanceType", "m1.small"),
            subnet_id=properties.get("SubnetId"),
            key_name=properties.get("KeyName"),
        )
        return reservation.instances[0]

    @property
    def physical_resource_id(self):
        return self.id

    def start(self, *args, **kwargs):
        self._state.name = "running"
        self._state.code = 16

    def stop(self, *args, **kwargs):
        self._state.name = "stopped"
        self._state.code = 80

    def terminate(self, *args, **kwargs):
        self._state.name = "terminated"
        self._state.code = 48

    def reboot(self, *args, **kwargs):
        self._state.name = "running"
        self._state.code = 16


class InstanceBackend(object):

    def __init__(self):
        self.reservations = {}
        super(InstanceBackend, self).__init__()

    def get_instance(self, instance_id):
        for instance in self.all_instances():
            if instance.id == instance_id:
                return instance

    def add_instances(self, image_id, count, user_data, security_group_names,
                      **kwargs):
        new_reservation = Reservation()
        new_reservation.id = random_reservation_id()

        security_groups = [self.get_security_group_from_name(name)
                           for name in security_group_names]
        security_groups.extend(self.get_security_group_from_id(sg_id)
                               for sg_id in kwargs.pop("security_group_ids", []))
        for index in range(count):
            new_instance = Instance(
                image_id,
                user_data,
                security_groups,
                **kwargs
            )
            new_reservation.instances.append(new_instance)
        self.reservations[new_reservation.id] = new_reservation
        return new_reservation

    def start_instances(self, instance_ids):
        started_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.start()
                started_instances.append(instance)

        return started_instances

    def stop_instances(self, instance_ids):
        stopped_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.stop()
                stopped_instances.append(instance)

        return stopped_instances

    def terminate_instances(self, instance_ids):
        terminated_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.terminate()
                terminated_instances.append(instance)

        return terminated_instances

    def reboot_instances(self, instance_ids):
        rebooted_instances = []
        for instance in self.all_instances():
            if instance.id in instance_ids:
                instance.reboot()
                rebooted_instances.append(instance)

        return rebooted_instances

    def modify_instance_attribute(self, instance_id, key, value):
        instance = self.get_instance(instance_id)
        setattr(instance, key, value)
        return instance

    def describe_instance_attribute(self, instance_id, key):
        instance = self.get_instance(instance_id)
        value = getattr(instance, key)
        return instance, value

    def all_instances(self):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                instances.append(instance)
        return instances

    def get_instance_by_id(self, instance_id):
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.id == instance_id:
                    return instance

    def get_reservations_by_instance_ids(self, instance_ids):
        """ Go through all of the reservations and filter to only return those
        associated with the given instance_ids.
        """
        reservations = []
        for reservation in self.all_reservations(make_copy=True):
            reservation_instance_ids = [instance.id for instance in reservation.instances]
            matching_reservation = any(instance_id in reservation_instance_ids for instance_id in instance_ids)
            if matching_reservation:
                # We need to make a copy of the reservation because we have to modify the
                # instances to limit to those requested
                reservation.instances = [instance for instance in reservation.instances if instance.id in instance_ids]
                reservations.append(reservation)
        found_instance_ids = [instance.id for reservation in reservations for instance in reservation.instances]
        if len(found_instance_ids) != len(instance_ids):
            invalid_id = list(set(instance_ids).difference(set(found_instance_ids)))[0]
            raise InvalidIdError(invalid_id)
        return reservations

    def all_reservations(self, make_copy=False):
        if make_copy:
            # Return copies so that other functions can modify them with changing
            # the originals
            return [copy.deepcopy(reservation) for reservation in self.reservations.values()]
        else:
            return [reservation for reservation in self.reservations.values()]


class KeyPairBackend(object):

    def __init__(self):
        self.keypairs = defaultdict(dict)
        super(KeyPairBackend, self).__init__()

    def create_key_pair(self, name):
        if name in self.keypairs:
            raise InvalidIdError(name)
        self.keypairs[name] = keypair = random_key_pair()
        keypair['name'] = name
        return keypair

    def delete_key_pair(self, name):
        if name in self.keypairs:
            self.keypairs.pop(name)
        return True

    def describe_key_pairs(self, filter_names=None):
        results = []
        for name, keypair in self.keypairs.iteritems():
            if not filter_names or name in filter_names:
                keypair['name'] = name
                results.append(keypair)
        return results


class TagBackend(object):

    def __init__(self):
        self.tags = defaultdict(dict)
        super(TagBackend, self).__init__()

    def create_tag(self, resource_id, key, value):
        self.tags[resource_id][key] = value
        return value

    def delete_tag(self, resource_id, key):
        return self.tags[resource_id].pop(key)

    def describe_tags(self, filter_resource_ids=None):
        results = []
        for resource_id, tags in self.tags.iteritems():
            ami = 'ami' in resource_id
            for key, value in tags.iteritems():
                if not filter_resource_ids or resource_id in filter_resource_ids:
                    # If we're not filtering, or we are filtering and this
                    # resource id is in the filter list, add this tag
                    result = {
                        'resource_id': resource_id,
                        'key': key,
                        'value': value,
                        'resource_type': 'image' if ami else 'instance',
                    }
                    results.append(result)
        return results


class Ami(TaggedEC2Instance):
    def __init__(self, ami_id, instance, name, description):
        self.id = ami_id
        self.instance = instance
        self.instance_id = instance.id
        self.name = name
        self.description = description

        self.virtualization_type = instance.virtualization_type
        self.kernel_id = instance.kernel


class AmiBackend(object):
    def __init__(self):
        self.amis = {}
        super(AmiBackend, self).__init__()

    def create_image(self, instance_id, name, description):
        # TODO: check that instance exists and pull info from it.
        ami_id = random_ami_id()
        instance = self.get_instance(instance_id)
        if not instance:
            return None
        ami = Ami(ami_id, instance, name, description)
        self.amis[ami_id] = ami
        return ami

    def describe_images(self, ami_ids=()):
        images = []
        for ami_id in ami_ids:
            if ami_id in self.amis:
                images.append(self.amis[ami_id])
            else:
                raise InvalidIdError(ami_id)
        return images or self.amis.values()

    def deregister_image(self, ami_id):
        if ami_id in self.amis:
            self.amis.pop(ami_id)
            return True
        return False


class Region(object):
    def __init__(self, name, endpoint):
        self.name = name
        self.endpoint = endpoint


class Zone(object):
    def __init__(self, name, region_name):
        self.name = name
        self.region_name = region_name


class RegionsAndZonesBackend(object):
    regions = [
        Region("eu-west-1", "ec2.eu-west-1.amazonaws.com"),
        Region("sa-east-1", "ec2.sa-east-1.amazonaws.com"),
        Region("us-east-1", "ec2.us-east-1.amazonaws.com"),
        Region("ap-northeast-1", "ec2.ap-northeast-1.amazonaws.com"),
        Region("us-west-2", "ec2.us-west-2.amazonaws.com"),
        Region("us-west-1", "ec2.us-west-1.amazonaws.com"),
        Region("ap-southeast-1", "ec2.ap-southeast-1.amazonaws.com"),
        Region("ap-southeast-2", "ec2.ap-southeast-2.amazonaws.com"),
    ]

    # TODO: cleanup. For now, pretend everything is us-east-1. 'merica.
    zones = [
        Zone("us-east-1a", "us-east-1"),
        Zone("us-east-1b", "us-east-1"),
        Zone("us-east-1c", "us-east-1"),
        Zone("us-east-1d", "us-east-1"),
        Zone("us-east-1e", "us-east-1"),
    ]

    def describe_regions(self):
        return self.regions

    def describe_availability_zones(self):
        return self.zones

    def get_zone_by_name(self, name):
        for zone in self.zones:
            if zone.name == name:
                return zone


class SecurityRule(object):
    def __init__(self, ip_protocol, from_port, to_port, ip_ranges, source_groups):
        self.ip_protocol = ip_protocol
        self.from_port = from_port
        self.to_port = to_port
        self.ip_ranges = ip_ranges or []
        self.source_groups = source_groups

    @property
    def unique_representation(self):
        return "{0}-{1}-{2}-{3}-{4}".format(
               self.ip_protocol,
               self.from_port,
               self.to_port,
               self.ip_ranges,
               self.source_groups
        )

    def __eq__(self, other):
        return self.unique_representation == other.unique_representation


class SecurityGroup(object):
    def __init__(self, group_id, name, description, vpc_id=None):
        self.id = group_id
        self.name = name
        self.description = description
        self.ingress_rules = []
        self.egress_rules = []
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc_id = properties.get('VpcId')
        security_group = ec2_backend.create_security_group(
            name=resource_name,
            description=properties.get('GroupDescription'),
            vpc_id=vpc_id,
        )

        for ingress_rule in properties.get('SecurityGroupIngress', []):
            source_group_id = ingress_rule.get('SourceSecurityGroupId')

            ec2_backend.authorize_security_group_ingress(
                group_name=security_group.name,
                group_id=security_group.id,
                ip_protocol=ingress_rule['IpProtocol'],
                from_port=ingress_rule['FromPort'],
                to_port=ingress_rule['ToPort'],
                ip_ranges=ingress_rule.get('CidrIp'),
                source_group_ids=[source_group_id],
                vpc_id=vpc_id,
            )

        return security_group

    @property
    def physical_resource_id(self):
        return self.id


class SecurityGroupBackend(object):

    def __init__(self):
        # the key in the dict group is the vpc_id or None (non-vpc)
        self.groups = defaultdict(dict)
        super(SecurityGroupBackend, self).__init__()

    def create_security_group(self, name, description, vpc_id=None, force=False):
        group_id = random_security_group_id()
        if not force:
            existing_group = self.get_security_group_from_name(name, vpc_id)
            if existing_group:
                return None
        group = SecurityGroup(group_id, name, description, vpc_id=vpc_id)

        self.groups[vpc_id][group_id] = group
        return group

    def describe_security_groups(self):
        return itertools.chain(*[x.values() for x in self.groups.values()])

    def delete_security_group(self, name=None, group_id=None):
        if group_id:
            # loop over all the SGs, find the right one
            for vpc in self.groups.values():
                if group_id in vpc:
                    return vpc.pop(group_id)
        elif name:
            # Group Name.  Has to be in standard EC2, VPC needs to be identified by group_id
            group = self.get_security_group_from_name(name)
            if group:
                return self.groups[None].pop(group.id)

    def get_security_group_from_id(self, group_id):
        # 2 levels of chaining necessary since it's a complex structure
        all_groups = itertools.chain.from_iterable([x.values() for x in self.groups.values()])

        for group in all_groups:
            if group.id == group_id:
                return group

    def get_security_group_from_name(self, name, vpc_id=None):
        for group_id, group in self.groups[vpc_id].iteritems():
            if group.name == name:
                return group

        if name == 'default':
            # If the request is for the default group and it does not exist, create it
            default_group = ec2_backend.create_security_group("default", "The default security group", force=True)
            return default_group

    def authorize_security_group_ingress(self,
                                         group_name,
                                         group_id,
                                         ip_protocol,
                                         from_port,
                                         to_port,
                                         ip_ranges,
                                         source_group_names=None,
                                         source_group_ids=None,
                                         vpc_id=None):
        # to auth a group in a VPC you need the group_id the name isn't enough

        if group_name:
            group = self.get_security_group_from_name(group_name, vpc_id)
        elif group_id:
            group = self.get_security_group_from_id(group_id)

        if ip_ranges and not isinstance(ip_ranges, list):
            ip_ranges = [ip_ranges]

        source_group_names = source_group_names if source_group_names else []
        source_group_ids = source_group_ids if source_group_ids else []

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        # for VPCs
        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(ip_protocol, from_port, to_port, ip_ranges, source_groups)
        group.ingress_rules.append(security_rule)

    def revoke_security_group_ingress(self,
                                      group_name,
                                      group_id,
                                      ip_protocol,
                                      from_port,
                                      to_port,
                                      ip_ranges,
                                      source_group_names=None,
                                      source_group_ids=None,
                                      vpc_id=None):

        if group_name:
            group = self.get_security_group_from_name(group_name, vpc_id)
        elif group_id:
            group = self.get_security_group_from_id(group_id)

        source_groups = []
        for source_group_name in source_group_names:
            source_group = self.get_security_group_from_name(source_group_name, vpc_id)
            if source_group:
                source_groups.append(source_group)

        for source_group_id in source_group_ids:
            source_group = self.get_security_group_from_id(source_group_id)
            if source_group:
                source_groups.append(source_group)

        security_rule = SecurityRule(ip_protocol, from_port, to_port, ip_ranges, source_groups)
        if security_rule in group.ingress_rules:
            group.ingress_rules.remove(security_rule)
            return security_rule
        return False


class VolumeAttachment(object):
    def __init__(self, volume, instance, device):
        self.volume = volume
        self.instance = instance
        self.device = device

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        instance_id = properties['InstanceId']
        volume_id = properties['VolumeId']

        attachment = ec2_backend.attach_volume(
            volume_id=volume_id,
            instance_id=instance_id,
            device_path=properties['Device'],
        )
        return attachment


class Volume(object):
    def __init__(self, volume_id, size, zone):
        self.id = volume_id
        self.size = size
        self.zone = zone
        self.attachment = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        volume = ec2_backend.create_volume(
            size=properties.get('Size'),
            zone_name=properties.get('AvailabilityZone'),
        )
        return volume

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def status(self):
        if self.attachment:
            return 'in-use'
        else:
            return 'available'


class Snapshot(object):
    def __init__(self, snapshot_id, volume, description):
        self.id = snapshot_id
        self.volume = volume
        self.description = description


class EBSBackend(object):
    def __init__(self):
        self.volumes = {}
        self.attachments = {}
        self.snapshots = {}
        super(EBSBackend, self).__init__()

    def create_volume(self, size, zone_name):
        volume_id = random_volume_id()
        zone = self.get_zone_by_name(zone_name)
        volume = Volume(volume_id, size, zone)
        self.volumes[volume_id] = volume
        return volume

    def describe_volumes(self):
        return self.volumes.values()

    def delete_volume(self, volume_id):
        if volume_id in self.volumes:
            return self.volumes.pop(volume_id)
        return False

    def attach_volume(self, volume_id, instance_id, device_path):
        volume = self.volumes.get(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        volume.attachment = VolumeAttachment(volume, instance, device_path)
        return volume.attachment

    def detach_volume(self, volume_id, instance_id, device_path):
        volume = self.volumes.get(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        old_attachment = volume.attachment
        volume.attachment = None
        return old_attachment

    def create_snapshot(self, volume_id, description):
        snapshot_id = random_snapshot_id()
        volume = self.volumes.get(volume_id)
        snapshot = Snapshot(snapshot_id, volume, description)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def describe_snapshots(self):
        return self.snapshots.values()

    def delete_snapshot(self, snapshot_id):
        if snapshot_id in self.snapshots:
            return self.snapshots.pop(snapshot_id)
        return False


class VPC(TaggedEC2Instance):
    def __init__(self, vpc_id, cidr_block):
        self.id = vpc_id
        self.cidr_block = cidr_block
        self.dhcp_options = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc = ec2_backend.create_vpc(
            cidr_block=properties['CidrBlock'],
        )
        return vpc

    @property
    def physical_resource_id(self):
        return self.id


class VPCBackend(object):
    def __init__(self):
        self.vpcs = {}
        super(VPCBackend, self).__init__()

    def create_vpc(self, cidr_block):
        vpc_id = random_vpc_id()
        vpc = VPC(vpc_id, cidr_block)
        self.vpcs[vpc_id] = vpc
        return vpc

    def get_vpc(self, vpc_id):
        return self.vpcs.get(vpc_id)

    def get_all_vpcs(self):
        return self.vpcs.values()

    def delete_vpc(self, vpc_id):
        vpc = self.vpcs.pop(vpc_id, None)
        if vpc and vpc.dhcp_options:
            vpc.dhcp_options.vpc = None
            self.delete_dhcp_options_set(vpc.dhcp_options.id)
            vpc.dhcp_options = None
        return vpc


class Subnet(TaggedEC2Instance):
    def __init__(self, subnet_id, vpc_id, cidr_block):
        self.id = subnet_id
        self.vpc_id = vpc_id
        self.cidr_block = cidr_block

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc_id = properties['VpcId']
        subnet = ec2_backend.create_subnet(
            vpc_id=vpc_id,
            cidr_block=properties['CidrBlock']
        )
        return subnet

    @property
    def physical_resource_id(self):
        return self.id


class SubnetBackend(object):
    def __init__(self):
        self.subnets = {}
        super(SubnetBackend, self).__init__()

    def create_subnet(self, vpc_id, cidr_block):
        subnet_id = random_subnet_id()
        subnet = Subnet(subnet_id, vpc_id, cidr_block)
        self.subnets[subnet_id] = subnet
        return subnet

    def get_all_subnets(self):
        return self.subnets.values()

    def delete_subnet(self, subnet_id):
        return self.subnets.pop(subnet_id, None)


class SubnetRouteTableAssociation(object):
    def __init__(self, route_table_id, subnet_id):
        self.route_table_id = route_table_id
        self.subnet_id = subnet_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        route_table_id = properties['RouteTableId']
        subnet_id = properties['SubnetId']

        subnet_association = ec2_backend.create_subnet_association(
            route_table_id=route_table_id,
            subnet_id=subnet_id,
        )
        return subnet_association


class SubnetRouteTableAssociationBackend(object):
    def __init__(self):
        self.subnet_associations = {}
        super(SubnetRouteTableAssociationBackend, self).__init__()

    def create_subnet_association(self, route_table_id, subnet_id):
        subnet_association = SubnetRouteTableAssociation(route_table_id, subnet_id)
        self.subnet_associations["{0}:{1}".format(route_table_id, subnet_id)] = subnet_association
        return subnet_association


class RouteTable(object):
    def __init__(self, route_table_id, vpc_id):
        self.id = route_table_id
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        vpc_id = properties['VpcId']
        route_table = ec2_backend.create_route_table(
            vpc_id=vpc_id,
        )
        return route_table

    @property
    def physical_resource_id(self):
        return self.id


class RouteTableBackend(object):
    def __init__(self):
        self.route_tables = {}
        super(RouteTableBackend, self).__init__()

    def create_route_table(self, vpc_id):
        route_table_id = random_route_table_id()
        route_table = RouteTable(route_table_id, vpc_id)
        self.route_tables[route_table_id] = route_table
        return route_table


class Route(object):
    def __init__(self, route_table_id, destination_cidr_block, gateway_id):
        self.route_table_id = route_table_id
        self.destination_cidr_block = destination_cidr_block
        self.gateway_id = gateway_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        gateway_id = properties.get('GatewayId')
        route_table_id = properties['RouteTableId']
        route_table = ec2_backend.create_route(
            route_table_id=route_table_id,
            destination_cidr_block=properties['DestinationCidrBlock'],
            gateway_id=gateway_id,
        )
        return route_table


class RouteBackend(object):
    def __init__(self):
        self.routes = {}
        super(RouteBackend, self).__init__()

    def create_route(self, route_table_id, destination_cidr_block, gateway_id):
        route = Route(route_table_id, destination_cidr_block, gateway_id)
        self.routes[destination_cidr_block] = route
        return route


class InternetGateway(object):
    def __init__(self, gateway_id):
        self.id = gateway_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        return ec2_backend.create_gateway()

    @property
    def physical_resource_id(self):
        return self.id


class InternetGatewayBackend(object):
    def __init__(self):
        self.gateways = {}
        super(InternetGatewayBackend, self).__init__()

    def create_gateway(self):
        gateway_id = random_gateway_id()
        gateway = InternetGateway(gateway_id)
        self.gateways[gateway_id] = gateway
        return gateway


class VPCGatewayAttachment(object):
    def __init__(self, gateway_id, vpc_id):
        self.gateway_id = gateway_id
        self.vpc_id = vpc_id

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        return ec2_backend.create_vpc_gateway_attachment(
            gateway_id=properties['InternetGatewayId'],
            vpc_id=properties['VpcId'],
        )

    @property
    def physical_resource_id(self):
        return self.id


class VPCGatewayAttachmentBackend(object):
    def __init__(self):
        self.gateway_attachments = {}
        super(VPCGatewayAttachmentBackend, self).__init__()

    def create_vpc_gateway_attachment(self, vpc_id, gateway_id):
        attachment = VPCGatewayAttachment(vpc_id, gateway_id)
        self.gateway_attachments[gateway_id] = attachment
        return attachment


class SpotInstanceRequest(object):
    def __init__(self, spot_request_id, price, image_id, type, valid_from,
                 valid_until, launch_group, availability_zone_group, key_name,
                 security_groups, user_data, instance_type, placement, kernel_id,
                 ramdisk_id, monitoring_enabled, subnet_id):
        self.id = spot_request_id
        self.state = "open"
        self.price = price
        self.image_id = image_id
        self.type = type
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.launch_group = launch_group
        self.availability_zone_group = availability_zone_group
        self.key_name = key_name
        self.user_data = user_data
        self.instance_type = instance_type
        self.placement = placement
        self.kernel_id = kernel_id
        self.ramdisk_id = ramdisk_id
        self.monitoring_enabled = monitoring_enabled
        self.subnet_id = subnet_id

        self.security_groups = []
        if security_groups:
            for group_name in security_groups:
                group = ec2_backend.get_security_group_from_name(group_name)
                if group:
                    self.security_groups.append(group)
        else:
            # If not security groups, add the default
            default_group = ec2_backend.get_security_group_from_name("default")
            self.security_groups.append(default_group)


class SpotRequestBackend(object):
    def __init__(self):
        self.spot_instance_requests = {}
        super(SpotRequestBackend, self).__init__()

    def request_spot_instances(self, price, image_id, count, type, valid_from,
                               valid_until, launch_group, availability_zone_group,
                               key_name, security_groups, user_data,
                               instance_type, placement, kernel_id, ramdisk_id,
                               monitoring_enabled, subnet_id):
        requests = []
        for _ in range(count):
            spot_request_id = random_spot_request_id()
            request = SpotInstanceRequest(
                spot_request_id, price, image_id, type, valid_from, valid_until,
                launch_group, availability_zone_group, key_name, security_groups,
                user_data, instance_type, placement, kernel_id, ramdisk_id,
                monitoring_enabled, subnet_id
            )
            self.spot_instance_requests[spot_request_id] = request
            requests.append(request)
        return requests

    def describe_spot_instance_requests(self):
        return self.spot_instance_requests.values()

    def cancel_spot_instance_requests(self, request_ids):
        requests = []
        for request_id in request_ids:
            requests.append(self.spot_instance_requests.pop(request_id))
        return requests


class ElasticAddress(object):
    def __init__(self, domain):
        self.public_ip = random_ip()
        self.allocation_id = random_eip_allocation_id() if domain == "vpc" else None
        self.domain = domain
        self.instance = None
        self.association_id = None

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        eip = ec2_backend.allocate_address(
            domain=properties['Domain']
        )

        instance_id = properties.get('InstanceId')
        if instance_id:
            instance = ec2_backend.get_instance_by_id(instance_id)
            ec2_backend.associate_address(instance, eip.public_ip)

        return eip

    @property
    def physical_resource_id(self):
        return self.allocation_id


class ElasticAddressBackend(object):

    def __init__(self):
        self.addresses = []
        super(ElasticAddressBackend, self).__init__()

    def allocate_address(self, domain):
        address = ElasticAddress(domain)
        self.addresses.append(address)
        return address

    def address_by_ip(self, ips):
        return [address for address in self.addresses
                if address.public_ip in ips]

    def address_by_allocation(self, allocation_ids):
        return [address for address in self.addresses
                if address.allocation_id in allocation_ids]

    def address_by_association(self, association_ids):
        return [address for address in self.addresses
                if address.association_id in association_ids]

    def associate_address(self, instance, address=None, allocation_id=None, reassociate=False):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])
        eip = eips[0] if len(eips) > 0 else None

        if eip and eip.instance is None or reassociate:
            eip.instance = instance
            if eip.domain == "vpc":
                eip.association_id = random_eip_association_id()
            return eip
        else:
            return None

    def describe_addresses(self):
        return self.addresses

    def disassociate_address(self, address=None, association_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif association_id:
            eips = self.address_by_association([association_id])

        if eips:
            eip = eips[0]
            eip.instance = None
            eip.association_id = None
            return True
        else:
            return False

    def release_address(self, address=None, allocation_id=None):
        eips = []
        if address:
            eips = self.address_by_ip([address])
        elif allocation_id:
            eips = self.address_by_allocation([allocation_id])

        if eips:
            eip = eips[0]
            self.disassociate_address(address=eip.public_ip)
            eip.allocation_id = None
            self.addresses.remove(eip)
            return True
        else:
            return False


class DHCPOptionsSet(TaggedEC2Instance):
    def __init__(self, domain_name_servers=None, domain_name=None,
                 ntp_servers=None, netbios_name_servers=None,
                 netbios_node_type=None):
        self._options = {
            "domain-name-servers": domain_name_servers,
            "domain-name": domain_name,
            "ntp-servers": ntp_servers,
            "netbios-name-servers": netbios_name_servers,
            "netbios-node-type": netbios_node_type,
        }
        self.id = random_dhcp_option_id()
        self.vpc = None

    @property
    def options(self):
        return self._options


class DHCPOptionsSetBackend(object):
    def __init__(self):
        self.dhcp_options_sets = {}
        super(DHCPOptionsSetBackend, self).__init__()

    def associate_dhcp_options(self, dhcp_options, vpc):
        dhcp_options.vpc = vpc
        vpc.dhcp_options = dhcp_options

    def create_dhcp_options(
            self, domain_name_servers=None, domain_name=None,
            ntp_servers=None, netbios_name_servers=None,
            netbios_node_type=None):
        options = DHCPOptionsSet(
            domain_name_servers, domain_name, ntp_servers,
            netbios_name_servers, netbios_node_type
        )
        self.dhcp_options_sets[options.id] = options
        return options

    def describe_dhcp_options(self, options_ids=None):
        options_sets = []
        for option_id in options_ids or []:
            if option_id in self.dhcp_options_sets:
                options_sets.append(self.dhcp_options_sets[option_id])
            else:
                raise InvalidDHCPOptionsIdError(option_id)
        return options_sets or self.dhcp_options_sets.values()

    def delete_dhcp_options_set(self, options_id):
        if options_id in self.dhcp_options_sets:
            if self.dhcp_options_sets[options_id].vpc:
                raise DependencyViolationError("Cannot delete assigned DHCP options.")
            self.dhcp_options_sets.pop(options_id)
        else:
            raise InvalidDHCPOptionsIdError(options_id)
        return True


class EC2Backend(BaseBackend, InstanceBackend, TagBackend, AmiBackend,
                 RegionsAndZonesBackend, SecurityGroupBackend, EBSBackend,
                 VPCBackend, SubnetBackend, SubnetRouteTableAssociationBackend,
                 RouteTableBackend, RouteBackend, InternetGatewayBackend,
                 VPCGatewayAttachmentBackend, SpotRequestBackend,
                 ElasticAddressBackend, KeyPairBackend, DHCPOptionsSetBackend):
    pass


ec2_backend = EC2Backend()

########NEW FILE########
__FILENAME__ = amazon_dev_pay
from moto.core.responses import BaseResponse


class AmazonDevPay(BaseResponse):
    def confirm_product_instance(self):
        raise NotImplementedError('AmazonDevPay.confirm_product_instance is not yet implemented')

########NEW FILE########
__FILENAME__ = amis
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.exceptions import InvalidIdError
from moto.ec2.utils import instance_ids_from_querystring, image_ids_from_querystring


class AmisResponse(BaseResponse):
    def create_image(self):
        name = self.querystring.get('Name')[0]
        if "Description" in self.querystring:
            description = self.querystring.get('Description')[0]
        else:
            description = ""
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        image = ec2_backend.create_image(instance_id, name, description)
        if not image:
            return "There is not instance with id {0}".format(instance_id), dict(status=404)
        template = Template(CREATE_IMAGE_RESPONSE)
        return template.render(image=image)

    def deregister_image(self):
        ami_id = self.querystring.get('ImageId')[0]
        success = ec2_backend.deregister_image(ami_id)
        template = Template(DEREGISTER_IMAGE_RESPONSE)
        rendered = template.render(success=str(success).lower())
        if success:
            return rendered
        else:
            return rendered, dict(status=404)

    def describe_image_attribute(self):
        raise NotImplementedError('AMIs.describe_image_attribute is not yet implemented')

    def describe_images(self):
        ami_ids = image_ids_from_querystring(self.querystring)
        try:
            images = ec2_backend.describe_images(ami_ids=ami_ids)
        except InvalidIdError as exc:
            template = Template(DESCRIBE_IMAGES_INVALID_IMAGE_ID_RESPONSE)
            return template.render(image_id=exc.id), dict(status=400)
        else:
            template = Template(DESCRIBE_IMAGES_RESPONSE)
            return template.render(images=images)

    def modify_image_attribute(self):
        raise NotImplementedError('AMIs.modify_image_attribute is not yet implemented')

    def register_image(self):
        raise NotImplementedError('AMIs.register_image is not yet implemented')

    def reset_image_attribute(self):
        raise NotImplementedError('AMIs.reset_image_attribute is not yet implemented')


CREATE_IMAGE_RESPONSE = """<CreateImageResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
</CreateImageResponse>"""

# TODO almost all of these params should actually be templated based on the ec2 image
DESCRIBE_IMAGES_RESPONSE = """<DescribeImagesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <imagesSet>
    {% for image in images %}
        <item>
          <imageId>{{ image.id }}</imageId>
          <imageLocation>amazon/getting-started</imageLocation>
          <imageState>available</imageState>
          <imageOwnerId>111122223333</imageOwnerId>
          <isPublic>true</isPublic>
          <architecture>i386</architecture>
          <imageType>machine</imageType>
          <kernelId>{{ image.kernel_id }}</kernelId>
          <ramdiskId>ari-1a2b3c4d</ramdiskId>
          <imageOwnerAlias>amazon</imageOwnerAlias>
          <name>{{ image.name }}</name>
          <description>{{ image.description }}</description>
          <rootDeviceType>ebs</rootDeviceType>
          <rootDeviceName>/dev/sda</rootDeviceName>
          <blockDeviceMapping>
            <item>
              <deviceName>/dev/sda1</deviceName>
              <ebs>
                <snapshotId>snap-1a2b3c4d</snapshotId>
                <volumeSize>15</volumeSize>
                <deleteOnTermination>false</deleteOnTermination>
                <volumeType>standard</volumeType>
              </ebs>
            </item>
          </blockDeviceMapping>
          <virtualizationType>{{ image.virtualization_type }}</virtualizationType>
          <tagSet>
            {% for tag in image.get_tags() %}
              <item>
                <resourceId>{{ tag.resource_id }}</resourceId>
                <resourceType>{{ tag.resource_type }}</resourceType>
                <key>{{ tag.key }}</key>
                <value>{{ tag.value }}</value>
              </item>
            {% endfor %}
          </tagSet>
          <hypervisor>xen</hypervisor>
        </item>
    {% endfor %}
  </imagesSet>
</DescribeImagesResponse>"""

DESCRIBE_IMAGE_RESPONSE = """<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <imageId>{{ image.id }}</imageId>
   <{{ key }}>
     <value>{{ value }}</value>
   </{{key }}>
</DescribeImageAttributeResponse>"""


DESCRIBE_IMAGES_INVALID_IMAGE_ID_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>InvalidAMIID.NotFound</Code><Message>The image id '[{{ image_id }}]' does not exist</Message></Error></Errors><RequestID>59dbff89-35bd-4eac-99ed-be587EXAMPLE</RequestID></Response>
"""

DEREGISTER_IMAGE_RESPONSE = """<DeregisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>{{ success }}</return>
</DeregisterImageResponse>"""

########NEW FILE########
__FILENAME__ = availability_zones_and_regions
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class AvailabilityZonesAndRegions(BaseResponse):
    def describe_availability_zones(self):
        zones = ec2_backend.describe_availability_zones()
        template = Template(DESCRIBE_ZONES_RESPONSE)
        return template.render(zones=zones)

    def describe_regions(self):
        regions = ec2_backend.describe_regions()
        template = Template(DESCRIBE_REGIONS_RESPONSE)
        return template.render(regions=regions)

DESCRIBE_REGIONS_RESPONSE = """<DescribeRegionsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <regionInfo>
      {% for region in regions %}
          <item>
             <regionName>{{ region.name }}</regionName>
             <regionEndpoint>{{ region.endpoint }}</regionEndpoint>
          </item>
      {% endfor %}
   </regionInfo>
</DescribeRegionsResponse>"""

DESCRIBE_ZONES_RESPONSE = """<DescribeAvailabilityZonesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <availabilityZoneInfo>
   {% for zone in zones %}
       <item>
          <zoneName>{{ zone.name }}</zoneName>
          <zoneState>available</zoneState>
          <regionName>{{ zone.region_name }}</regionName>
          <messageSet/>
       </item>
   {% endfor %}
   </availabilityZoneInfo>
</DescribeAvailabilityZonesResponse>"""

########NEW FILE########
__FILENAME__ = customer_gateways
from moto.core.responses import BaseResponse


class CustomerGateways(BaseResponse):
    def create_customer_gateway(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).create_customer_gateway is not yet implemented')

    def delete_customer_gateway(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).delete_customer_gateway is not yet implemented')

    def describe_customer_gateways(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).describe_customer_gateways is not yet implemented')

########NEW FILE########
__FILENAME__ = dhcp_options
from jinja2 import Template
from moto.core.responses import BaseResponse
from moto.ec2.utils import (
    dhcp_configuration_from_querystring,
    sequence_from_querystring)
from moto.ec2.models import ec2_backend
from moto.ec2.exceptions import(
    InvalidVPCIdError,
    InvalidParameterValueError,
)

NETBIOS_NODE_TYPES = [1, 2, 4, 8]


class DHCPOptions(BaseResponse):
    def associate_dhcp_options(self):
        dhcp_opt_id = self.querystring.get("DhcpOptionsId", [None])[0]
        vpc_id = self.querystring.get("VpcId", [None])[0]

        dhcp_opt = ec2_backend.describe_dhcp_options([dhcp_opt_id])[0]

        vpc = ec2_backend.get_vpc(vpc_id)
        if not vpc:
            raise InvalidVPCIdError(vpc_id)

        ec2_backend.associate_dhcp_options(dhcp_opt, vpc)

        template = Template(ASSOCIATE_DHCP_OPTIONS_RESPONSE)
        return template.render()

    def create_dhcp_options(self):
        dhcp_config = dhcp_configuration_from_querystring(self.querystring)

        # TODO validate we only got the options we know about

        domain_name_servers = dhcp_config.get("domain-name-servers", None)
        domain_name = dhcp_config.get("domain-name", None)
        ntp_servers = dhcp_config.get("ntp-servers", None)
        netbios_name_servers = dhcp_config.get("netbios-name-servers", None)
        netbios_node_type = dhcp_config.get("netbios-node-type", None)

        for field_value in domain_name_servers, ntp_servers, netbios_name_servers:
            if field_value and len(field_value) > 4:
                raise InvalidParameterValueError(",".join(field_value))

        if netbios_node_type and netbios_node_type[0] not in NETBIOS_NODE_TYPES:
            raise InvalidParameterValueError(netbios_node_type)

        dhcp_options_set = ec2_backend.create_dhcp_options(
            domain_name_servers=domain_name_servers,
            domain_name=domain_name,
            ntp_servers=ntp_servers,
            netbios_name_servers=netbios_name_servers,
            netbios_node_type=netbios_node_type
        )

        template = Template(CREATE_DHCP_OPTIONS_RESPONSE)
        return template.render(dhcp_options_set=dhcp_options_set)

    def delete_dhcp_options(self):
        # TODO InvalidDhcpOptionsId.Malformed

        delete_status = False

        if "DhcpOptionsId" in self.querystring:
            dhcp_opt_id = self.querystring["DhcpOptionsId"][0]

            delete_status = ec2_backend.delete_dhcp_options_set(dhcp_opt_id)

        template = Template(DELETE_DHCP_OPTIONS_RESPONSE)
        return template.render(delete_status=delete_status)

    def describe_dhcp_options(self):

        if "Filter.1.Name" in self.querystring:
            raise NotImplementedError("Filtering not supported in describe_dhcp_options.")
        elif "DhcpOptionsId.1" in self.querystring:
            dhcp_opt_ids = sequence_from_querystring("DhcpOptionsId", self.querystring)
            dhcp_opt = ec2_backend.describe_dhcp_options(dhcp_opt_ids)
        else:
            dhcp_opt = ec2_backend.describe_dhcp_options()
        template = Template(DESCRIBE_DHCP_OPTIONS_RESPONSE)
        return template.render(dhcp_options=dhcp_opt)


CREATE_DHCP_OPTIONS_RESPONSE = u"""
<CreateDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <dhcpOptions>
      <dhcpOptionsId>{{ dhcp_options_set.id }}</dhcpOptionsId>
      <dhcpConfigurationSet>
      {% for key, values in dhcp_options_set.options.iteritems() %}
        {{ values }}
        {% if values %}
        <item>
          <key>{{key}}</key>
          <valueSet>
            {% for value in values %}
            <item>
              <value>{{ value }}</value>
            </item>
            {% endfor %}
          </valueSet>
        </item>
        {% endif %}
      {% endfor %}
      </dhcpConfigurationSet>
      <tagSet>
        {% for tag in dhcp_options_set.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
  </dhcpOptions>
</CreateDhcpOptionsResponse>
"""

DELETE_DHCP_OPTIONS_RESPONSE = u"""
<DeleteDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>{{delete_status}}</return>
</DeleteDhcpOptionsResponse>
"""

DESCRIBE_DHCP_OPTIONS_RESPONSE = u"""
<DescribeDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <item>
    {% for dhcp_options_set in dhcp_options %}
    <dhcpOptions>
      <dhcpOptionsId>{{ dhcp_options_set.id }}</dhcpOptionsId>
      <dhcpConfigurationSet>
      {% for key, values in dhcp_options_set.options.iteritems() %}
        {{ values }}
        {% if values %}
        <item>
          <key>{{key}}</key>
          <valueSet>
            {% for value in values %}
            <item>
              <value>{{ value }}</value>
            </item>
            {% endfor %}
          </valueSet>
        </item>
        {% endif %}
      {% endfor %}
      </dhcpConfigurationSet>
      <tagSet>
        {% for tag in dhcp_options_set.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
    </dhcpOptions>
    {% endfor %}
  </item>
</DescribeDhcpOptionsResponse>
"""

ASSOCIATE_DHCP_OPTIONS_RESPONSE = u"""
<AssociateDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
<requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
<return>true</return>
</AssociateDhcpOptionsResponse>
"""

########NEW FILE########
__FILENAME__ = elastic_block_store
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class ElasticBlockStore(BaseResponse):
    def attach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]

        attachment = ec2_backend.attach_volume(volume_id, instance_id, device_path)
        if not attachment:
            return "", dict(status=404)
        template = Template(ATTACHED_VOLUME_RESPONSE)
        return template.render(attachment=attachment)

    def copy_snapshot(self):
        raise NotImplementedError('ElasticBlockStore.copy_snapshot is not yet implemented')

    def create_snapshot(self):
        description = None
        if 'Description' in self.querystring:
            description = self.querystring.get('Description')[0]
        volume_id = self.querystring.get('VolumeId')[0]
        snapshot = ec2_backend.create_snapshot(volume_id, description)
        template = Template(CREATE_SNAPSHOT_RESPONSE)
        return template.render(snapshot=snapshot)

    def create_volume(self):
        size = self.querystring.get('Size')[0]
        zone = self.querystring.get('AvailabilityZone')[0]
        volume = ec2_backend.create_volume(size, zone)
        template = Template(CREATE_VOLUME_RESPONSE)
        return template.render(volume=volume)

    def delete_snapshot(self):
        snapshot_id = self.querystring.get('SnapshotId')[0]
        success = ec2_backend.delete_snapshot(snapshot_id)
        if not success:
            # Snapshot doesn't exist
            return "Snapshot with id {0} does not exist".format(snapshot_id), dict(status=404)
        return DELETE_SNAPSHOT_RESPONSE

    def delete_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        success = ec2_backend.delete_volume(volume_id)
        if not success:
            # Volume doesn't exist
            return "Volume with id {0} does not exist".format(volume_id), dict(status=404)
        return DELETE_VOLUME_RESPONSE

    def describe_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.describe_snapshot_attribute is not yet implemented')

    def describe_snapshots(self):
        snapshots = ec2_backend.describe_snapshots()
        template = Template(DESCRIBE_SNAPSHOTS_RESPONSE)
        return template.render(snapshots=snapshots)

    def describe_volumes(self):
        volumes = ec2_backend.describe_volumes()
        template = Template(DESCRIBE_VOLUMES_RESPONSE)
        return template.render(volumes=volumes)

    def describe_volume_attribute(self):
        raise NotImplementedError('ElasticBlockStore.describe_volume_attribute is not yet implemented')

    def describe_volume_status(self):
        raise NotImplementedError('ElasticBlockStore.describe_volume_status is not yet implemented')

    def detach_volume(self):
        volume_id = self.querystring.get('VolumeId')[0]
        instance_id = self.querystring.get('InstanceId')[0]
        device_path = self.querystring.get('Device')[0]

        attachment = ec2_backend.detach_volume(volume_id, instance_id, device_path)
        if not attachment:
            # Volume wasn't attached
            return "Volume {0} can not be detached from {1} because it is not attached".format(volume_id, instance_id), dict(status=404)
        template = Template(DETATCH_VOLUME_RESPONSE)
        return template.render(attachment=attachment)

    def enable_volume_io(self):
        raise NotImplementedError('ElasticBlockStore.enable_volume_io is not yet implemented')

    def import_volume(self):
        raise NotImplementedError('ElasticBlockStore.import_volume is not yet implemented')

    def modify_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.modify_snapshot_attribute is not yet implemented')

    def modify_volume_attribute(self):
        raise NotImplementedError('ElasticBlockStore.modify_volume_attribute is not yet implemented')

    def reset_snapshot_attribute(self):
        raise NotImplementedError('ElasticBlockStore.reset_snapshot_attribute is not yet implemented')


CREATE_VOLUME_RESPONSE = """<CreateVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <volumeId>{{ volume.id }}</volumeId>
  <size>{{ volume.size }}</size>
  <snapshotId/>
  <availabilityZone>{{ volume.zone.name }}</availabilityZone>
  <status>creating</status>
  <createTime>YYYY-MM-DDTHH:MM:SS.000Z</createTime>
  <volumeType>standard</volumeType>
</CreateVolumeResponse>"""

DESCRIBE_VOLUMES_RESPONSE = """<DescribeVolumesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <volumeSet>
      {% for volume in volumes %}
          <item>
             <volumeId>{{ volume.id }}</volumeId>
             <size>{{ volume.size }}</size>
             <snapshotId/>
             <availabilityZone>{{ volume.zone.name }}</availabilityZone>
             <status>{{ volume.status }}</status>
             <createTime>YYYY-MM-DDTHH:MM:SS.SSSZ</createTime>
             <attachmentSet>
                {% if volume.attachment %}
                    <item>
                       <volumeId>{{ volume.id }}</volumeId>
                       <instanceId>{{ volume.attachment.instance.id }}</instanceId>
                       <device>{{ volume.attachment.device }}</device>
                       <status>attached</status>
                       <attachTime>YYYY-MM-DDTHH:MM:SS.SSSZ</attachTime>
                       <deleteOnTermination>false</deleteOnTermination>
                    </item>
                {% endif %}
             </attachmentSet>
             <volumeType>standard</volumeType>
          </item>
      {% endfor %}
   </volumeSet>
</DescribeVolumesResponse>"""

DELETE_VOLUME_RESPONSE = """<DeleteVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteVolumeResponse>"""

ATTACHED_VOLUME_RESPONSE = """<AttachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <volumeId>{{ attachment.volume.id }}</volumeId>
  <instanceId>{{ attachment.instance.id }}</instanceId>
  <device>{{ attachment.device }}</device>
  <status>attaching</status>
  <attachTime>YYYY-MM-DDTHH:MM:SS.000Z</attachTime>
</AttachVolumeResponse>"""

DETATCH_VOLUME_RESPONSE = """<DetachVolumeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <volumeId>{{ attachment.volume.id }}</volumeId>
   <instanceId>{{ attachment.instance.id }}</instanceId>
   <device>{{ attachment.device }}</device>
   <status>detaching</status>
   <attachTime>YYYY-MM-DDTHH:MM:SS.000Z</attachTime>
</DetachVolumeResponse>"""

CREATE_SNAPSHOT_RESPONSE = """<CreateSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <snapshotId>{{ snapshot.id }}</snapshotId>
  <volumeId>{{ snapshot.volume.id }}</volumeId>
  <status>pending</status>
  <startTime>YYYY-MM-DDTHH:MM:SS.000Z</startTime>
  <progress>60%</progress>
  <ownerId>111122223333</ownerId>
  <volumeSize>{{ snapshot.volume.size }}</volumeSize>
  <description>{{ snapshot.description }}</description>
</CreateSnapshotResponse>"""

DESCRIBE_SNAPSHOTS_RESPONSE = """<DescribeSnapshotsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <snapshotSet>
      {% for snapshot in snapshots %}
          <item>
             <snapshotId>{{ snapshot.id }}</snapshotId>
             <volumeId>{{ snapshot.volume.id }}</volumeId>
             <status>pending</status>
             <startTime>YYYY-MM-DDTHH:MM:SS.SSSZ</startTime>
             <progress>30%</progress>
             <ownerId>111122223333</ownerId>
             <volumeSize>{{ snapshot.volume.size }}</volumeSize>
             <description>{{ snapshot.description }}</description>
             <tagSet>
             </tagSet>
          </item>
      {% endfor %}
   </snapshotSet>
</DescribeSnapshotsResponse>"""

DELETE_SNAPSHOT_RESPONSE = """<DeleteSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSnapshotResponse>"""

########NEW FILE########
__FILENAME__ = elastic_ip_addresses
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import sequence_from_querystring


class ElasticIPAddresses(BaseResponse):
    def allocate_address(self):
        if "Domain" in self.querystring:
            domain = self.querystring.get('Domain')[0]
            if domain != "vpc":
                return "Invalid domain:{0}.".format(domain), dict(status=400)
        else:
            domain = "standard"
        address = ec2_backend.allocate_address(domain)
        template = Template(ALLOCATE_ADDRESS_RESPONSE)
        return template.render(address=address)

    def associate_address(self):
        if "InstanceId" in self.querystring:
            instance = ec2_backend.get_instance(self.querystring['InstanceId'][0])
        elif "NetworkInterfaceId" in self.querystring:
            raise NotImplementedError("Lookup by allocation id not implemented")
        else:
            return "Invalid request, expect InstanceId/NetworkId parameter.", dict(status=400)

        reassociate = False
        if "AllowReassociation" in self.querystring:
            reassociate = self.querystring['AllowReassociation'][0] == "true"

        if "PublicIp" in self.querystring:
            eip = ec2_backend.associate_address(instance, address=self.querystring['PublicIp'][0], reassociate=reassociate)
        elif "AllocationId" in self.querystring:
            eip = ec2_backend.associate_address(instance, allocation_id=self.querystring['AllocationId'][0], reassociate=reassociate)
        else:
            return "Invalid request, expect PublicIp/AllocationId parameter.", dict(status=400)

        if eip:
            template = Template(ASSOCIATE_ADDRESS_RESPONSE)
            return template.render(address=eip)
        else:
            return "Failed to associate address.", dict(status=400)

    def describe_addresses(self):
        template = Template(DESCRIBE_ADDRESS_RESPONSE)

        if "Filter.1.Name" in self.querystring:
            raise NotImplementedError("Filtering not supported in describe_address.")
        elif "PublicIp.1" in self.querystring:
            public_ips = sequence_from_querystring("PublicIp", self.querystring)
            addresses = ec2_backend.address_by_ip(public_ips)
        elif "AllocationId.1" in self.querystring:
            allocation_ids = sequence_from_querystring("AllocationId", self.querystring)
            addresses = ec2_backend.address_by_allocation(allocation_ids)
        else:
            addresses = ec2_backend.describe_addresses()
        return template.render(addresses=addresses)

    def disassociate_address(self):
        if "PublicIp" in self.querystring:
            disassociated = ec2_backend.disassociate_address(address=self.querystring['PublicIp'][0])
        elif "AssociationId" in self.querystring:
            disassociated = ec2_backend.disassociate_address(association_id=self.querystring['AssociationId'][0])
        else:
            return "Invalid request, expect PublicIp/AssociationId parameter.", dict(status=400)

        if disassociated:
            return Template(DISASSOCIATE_ADDRESS_RESPONSE).render()
        else:
            return "Address conresponding to PublicIp/AssociationIP not found.", dict(status=400)

    def release_address(self):
        if "PublicIp" in self.querystring:
            released = ec2_backend.release_address(address=self.querystring['PublicIp'][0])
        elif "AllocationId" in self.querystring:
            released = ec2_backend.release_address(allocation_id=self.querystring['AllocationId'][0])
        else:
            return "Invalid request, expect PublicIp/AllocationId parameter.", dict(status=400)

        if released:
            return Template(RELEASE_ADDRESS_RESPONSE).render()
        else:
            return "Address conresponding to PublicIp/AssociationIP not found.", dict(status=400)


ALLOCATE_ADDRESS_RESPONSE = """<AllocateAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <publicIp>{{ address.public_ip }}</publicIp>
  <domain>{{ address.domain }}</domain>
  {% if address.allocation_id %}
    <allocationId>{{ address.allocation_id }}</allocationId>
  {% endif %}
</AllocateAddressResponse>"""

ASSOCIATE_ADDRESS_RESPONSE = """<AssociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
  {% if address.association_id %}
    <associationId>{{ address.association_id }}</associationId>
  {% endif %}
</AssociateAddressResponse>"""

DESCRIBE_ADDRESS_RESPONSE = """<DescribeAddressesResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <addressesSet>
    {% for address in addresses %}
        <item>
          <publicIp>{{ address.public_ip }}</publicIp>
          <domain>{{ address.domain }}</domain>
          {% if address.instance %}
            <instanceId>{{ address.instance.id }}</instanceId>
          {% else %}
            <instanceId/>
          {% endif %}
          {% if address.allocation_id %}
            <allocationId>{{ address.allocation_id }}</allocationId>
          {% endif %}
          {% if address.association_id %}
            <associationId>{{ address.association_id }}</associationId>
          {% endif %}
        </item>
    {% endfor %}
  </addressesSet>
</DescribeAddressesResponse>"""

DISASSOCIATE_ADDRESS_RESPONSE = """<DisassociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DisassociateAddressResponse>"""

RELEASE_ADDRESS_RESPONSE = """<ReleaseAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-07-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ReleaseAddressResponse>"""

########NEW FILE########
__FILENAME__ = elastic_network_interfaces
from moto.core.responses import BaseResponse


class ElasticNetworkInterfaces(BaseResponse):
    def attach_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).attach_network_interface is not yet implemented')

    def create_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).create_network_interface is not yet implemented')

    def delete_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).delete_network_interface is not yet implemented')

    def describe_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).describe_network_interface_attribute is not yet implemented')

    def describe_network_interfaces(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).describe_network_interfaces is not yet implemented')

    def detach_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).detach_network_interface is not yet implemented')

    def modify_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).modify_network_interface_attribute is not yet implemented')

    def reset_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).reset_network_interface_attribute is not yet implemented')

########NEW FILE########
__FILENAME__ = general
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import instance_ids_from_querystring


class General(BaseResponse):
    def get_console_output(self):
        self.instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = self.instance_ids[0]
        instance = ec2_backend.get_instance(instance_id)
        if instance:
            template = Template(GET_CONSOLE_OUTPUT_RESULT)
            return template.render(instance=instance)
        else:
            return "", dict(status=404)


GET_CONSOLE_OUTPUT_RESULT = '''
<GetConsoleOutputResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>{{ instance.id }}</instanceId>
  <timestamp>2010-10-14T01:12:41.000Z</timestamp>
  <output>TGludXggdmVyc2lvbiAyLjYuMTYteGVuVSAoYnVpbGRlckBwYXRjaGJhdC5hbWF6b25zYSkgKGdj
YyB2ZXJzaW9uIDQuMC4xIDIwMDUwNzI3IChSZWQgSGF0IDQuMC4xLTUpKSAjMSBTTVAgVGh1IE9j
dCAyNiAwODo0MToyNiBTQVNUIDIwMDYKQklPUy1wcm92aWRlZCBwaHlzaWNhbCBSQU0gbWFwOgpY
ZW46IDAwMDAwMDAwMDAwMDAwMDAgLSAwMDAwMDAwMDZhNDAwMDAwICh1c2FibGUpCjk4ME1CIEhJ
R0hNRU0gYXZhaWxhYmxlLgo3MjdNQiBMT1dNRU0gYXZhaWxhYmxlLgpOWCAoRXhlY3V0ZSBEaXNh
YmxlKSBwcm90ZWN0aW9uOiBhY3RpdmUKSVJRIGxvY2t1cCBkZXRlY3Rpb24gZGlzYWJsZWQKQnVp
bHQgMSB6b25lbGlzdHMKS2VybmVsIGNvbW1hbmQgbGluZTogcm9vdD0vZGV2L3NkYTEgcm8gNApF
bmFibGluZyBmYXN0IEZQVSBzYXZlIGFuZCByZXN0b3JlLi4uIGRvbmUuCg==</output>
</GetConsoleOutputResponse>'''

########NEW FILE########
__FILENAME__ = instances
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from moto.ec2.models import ec2_backend
from moto.ec2.utils import instance_ids_from_querystring, filters_from_querystring, filter_reservations
from moto.ec2.exceptions import InvalidIdError


class InstanceResponse(BaseResponse):
    def describe_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        if instance_ids:
            try:
                reservations = ec2_backend.get_reservations_by_instance_ids(instance_ids)
            except InvalidIdError as exc:
                template = Template(EC2_INVALID_INSTANCE_ID)
                return template.render(instance_id=exc.id), dict(status=400)
        else:
            reservations = ec2_backend.all_reservations(make_copy=True)

        filter_dict = filters_from_querystring(self.querystring)
        reservations = filter_reservations(reservations, filter_dict)

        template = Template(EC2_DESCRIBE_INSTANCES)
        return template.render(reservations=reservations)

    def run_instances(self):
        min_count = int(self.querystring.get('MinCount', ['1'])[0])
        image_id = self.querystring.get('ImageId')[0]
        user_data = self.querystring.get('UserData')
        security_group_names = self._get_multi_param('SecurityGroup')
        security_group_ids = self._get_multi_param('SecurityGroupId')
        instance_type = self.querystring.get("InstanceType", ["m1.small"])[0]
        subnet_id = self.querystring.get("SubnetId", [None])[0]
        key_name = self.querystring.get("KeyName", [None])[0]
        new_reservation = ec2_backend.add_instances(
            image_id, min_count, user_data, security_group_names,
            instance_type=instance_type, subnet_id=subnet_id,
            key_name=key_name, security_group_ids=security_group_ids)
        template = Template(EC2_RUN_INSTANCES)
        return template.render(reservation=new_reservation)

    def terminate_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.terminate_instances(instance_ids)
        template = Template(EC2_TERMINATE_INSTANCES)
        return template.render(instances=instances)

    def reboot_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.reboot_instances(instance_ids)
        template = Template(EC2_REBOOT_INSTANCES)
        return template.render(instances=instances)

    def stop_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.stop_instances(instance_ids)
        template = Template(EC2_STOP_INSTANCES)
        return template.render(instances=instances)

    def start_instances(self):
        instance_ids = instance_ids_from_querystring(self.querystring)
        instances = ec2_backend.start_instances(instance_ids)
        template = Template(EC2_START_INSTANCES)
        return template.render(instances=instances)

    def describe_instance_attribute(self):
        # TODO this and modify below should raise IncorrectInstanceState if instance not in stopped state
        attribute = self.querystring.get("Attribute")[0]
        key = camelcase_to_underscores(attribute)
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        instance, value = ec2_backend.describe_instance_attribute(instance_id, key)
        template = Template(EC2_DESCRIBE_INSTANCE_ATTRIBUTE)
        return template.render(instance=instance, attribute=attribute, value=value)

    def modify_instance_attribute(self):
        attribute_key = None
        for key, value in self.querystring.iteritems():
            if '.Value' in key:
                attribute_key = key
                break

        if not attribute_key:
            return
        value = self.querystring.get(attribute_key)[0]
        normalized_attribute = camelcase_to_underscores(attribute_key.split(".")[0])
        instance_ids = instance_ids_from_querystring(self.querystring)
        instance_id = instance_ids[0]
        ec2_backend.modify_instance_attribute(instance_id, normalized_attribute, value)
        return EC2_MODIFY_INSTANCE_ATTRIBUTE


EC2_RUN_INSTANCES = """<RunInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <reservationId>{{ reservation.id }}</reservationId>
  <ownerId>111122223333</ownerId>
  <groupSet>
    <item>
      <groupId>sg-245f6a01</groupId>
      <groupName>default</groupName>
    </item>
  </groupSet>
  <instancesSet>
    {% for instance in reservation.instances %}
        <item>
          <instanceId>{{ instance.id }}</instanceId>
          <imageId>{{ instance.image_id }}</imageId>
          <instanceState>
            <code>0</code>
            <name>pending</name>
          </instanceState>
          <privateDnsName/>
          <dnsName/>
          <reason/>
          <keyName>{{ instance.key_name }}</keyName>
          <amiLaunchIndex>0</amiLaunchIndex>
          <instanceType>{{ instance.instance_type }}</instanceType>
          <launchTime>2007-08-07T11:51:50.000Z</launchTime>
          <placement>
            <availabilityZone>us-east-1b</availabilityZone>
            <groupName/>
            <tenancy>default</tenancy>
          </placement>
          <monitoring>
            <state>enabled</state>
          </monitoring>
          <subnetId>{{ instance.subnet_id }}</subnetId>
          <sourceDestCheck>true</sourceDestCheck>
          <groupSet>
             {% for group in instance.security_groups %}
             <item>
                <groupId>{{ group.id }}</groupId>
                <groupName>{{ group.name }}</groupName>
             </item>
             {% endfor %}
          </groupSet>
          <virtualizationType>paravirtual</virtualizationType>
          <clientToken/>
          <hypervisor>xen</hypervisor>
          <ebsOptimized>false</ebsOptimized>
        </item>
    {% endfor %}
  </instancesSet>
  </RunInstancesResponse>"""

EC2_DESCRIBE_INSTANCES = """<DescribeInstancesResponse xmlns='http://ec2.amazonaws.com/doc/2012-12-01/'>
  <requestId>fdcdcab1-ae5c-489e-9c33-4637c5dda355</requestId>
      <reservationSet>
        {% for reservation in reservations %}
          <item>
            <reservationId>{{ reservation.id }}</reservationId>
            <ownerId>111122223333</ownerId>
            <groupSet></groupSet>
            <instancesSet>
                {% for instance in reservation.instances %}
                  <item>
                    <instanceId>{{ instance.id }}</instanceId>
                    <imageId>{{ instance.image_id }}</imageId>
                    <instanceState>
                      <code>{{ instance._state.code }}</code>
                      <name>{{ instance._state.name }}</name>
                    </instanceState>
                    <privateDnsName>ip-10.0.0.12.ec2.internal</privateDnsName>
                    <dnsName>ec2-46.51.219.63.compute-1.amazonaws.com</dnsName>
                    <reason/>
                    <keyName>{{ instance.key_name }}</keyName>
                    <amiLaunchIndex>0</amiLaunchIndex>
                    <productCodes/>
                    <instanceType>{{ instance.instance_type }}</instanceType>
                    <launchTime>YYYY-MM-DDTHH:MM:SS+0000</launchTime>
                    <placement>
                      <availabilityZone>us-west-2a</availabilityZone>
                      <groupName/>
                      <tenancy>default</tenancy>
                    </placement>
                    <platform>windows</platform>
                    <monitoring>
                      <state>disabled</state>
                    </monitoring>
                    <subnetId>{{ instance.subnet_id }}</subnetId>
                    <vpcId>vpc-1a2b3c4d</vpcId>
                    <privateIpAddress>10.0.0.12</privateIpAddress>
                    <ipAddress>46.51.219.63</ipAddress>
                    <sourceDestCheck>true</sourceDestCheck>
                    <groupSet>
                      {% for group in instance.security_groups %}
                      <item>
                        <groupId>{{ group.id }}</groupId>
                        <groupName>{{ group.name }}</groupName>
                      </item>
                      {% endfor %}
                    </groupSet>
                    <architecture>x86_64</architecture>
                    <rootDeviceType>ebs</rootDeviceType>
                    <rootDeviceName>/dev/sda1</rootDeviceName>
                    <blockDeviceMapping />
                    <virtualizationType>hvm</virtualizationType>
                    <clientToken>ABCDE1234567890123</clientToken>
                    <tagSet>
                      {% for tag in instance.get_tags() %}
                        <item>
                          <resourceId>{{ tag.resource_id }}</resourceId>
                          <resourceType>{{ tag.resource_type }}</resourceType>
                          <key>{{ tag.key }}</key>
                          <value>{{ tag.value }}</value>
                        </item>
                      {% endfor %}
                    </tagSet>
                    <hypervisor>xen</hypervisor>
                    <networkInterfaceSet />
                  </item>
                {% endfor %}
            </instancesSet>
          </item>
        {% endfor %}
      </reservationSet>
</DescribeInstancesResponse>"""

EC2_TERMINATE_INSTANCES = """
<TerminateInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instancesSet>
    {% for instance in instances %}
      <item>
        <instanceId>{{ instance.id }}</instanceId>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
        <currentState>
          <code>32</code>
          <name>shutting-down</name>
        </currentState>
      </item>
    {% endfor %}
  </instancesSet>
</TerminateInstancesResponse>"""

EC2_STOP_INSTANCES = """
<StopInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instancesSet>
    {% for instance in instances %}
      <item>
        <instanceId>{{ instance.id }}</instanceId>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
        <currentState>
          <code>64</code>
          <name>stopping</name>
        </currentState>
      </item>
    {% endfor %}
  </instancesSet>
</StopInstancesResponse>"""

EC2_START_INSTANCES = """
<StartInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instancesSet>
    {% for instance in instances %}
      <item>
        <instanceId>{{ instance.id }}</instanceId>
        <previousState>
          <code>16</code>
          <name>running</name>
        </previousState>
        <currentState>
          <code>0</code>
          <name>pending</name>
        </currentState>
      </item>
    {% endfor %}
  </instancesSet>
</StartInstancesResponse>"""

EC2_REBOOT_INSTANCES = """<RebootInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RebootInstancesResponse>"""

EC2_DESCRIBE_INSTANCE_ATTRIBUTE = """<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>{{ instance.id }}</instanceId>
  <{{ attribute }}>
    <value>{{ value }}</value>
  </{{ attribute }}>
</DescribeInstanceAttributeResponse>"""

EC2_MODIFY_INSTANCE_ATTRIBUTE = """<ModifyInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ModifyInstanceAttributeResponse>"""


EC2_INVALID_INSTANCE_ID = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>InvalidInstanceID.NotFound</Code>
<Message>The instance ID '{{ instance_id }}' does not exist</Message></Error>
</Errors>
<RequestID>39070fe4-6f6d-4565-aecd-7850607e4555</RequestID></Response>"""

########NEW FILE########
__FILENAME__ = internet_gateways
from moto.core.responses import BaseResponse


class InternetGateways(BaseResponse):
    def attach_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).attach_internet_gateway is not yet implemented')

    def create_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).create_internet_gateway is not yet implemented')

    def delete_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).delete_internet_gateway is not yet implemented')

    def describe_internet_gateways(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).describe_internet_gateways is not yet implemented')

    def detach_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).detach_internet_gateway is not yet implemented')

########NEW FILE########
__FILENAME__ = ip_addresses
from moto.core.responses import BaseResponse


class IPAddresses(BaseResponse):
    def assign_private_ip_addresses(self):
        raise NotImplementedError('IPAddresses.assign_private_ip_addresses is not yet implemented')

    def unassign_private_ip_addresses(self):
        raise NotImplementedError('IPAddresses.unassign_private_ip_addresses is not yet implemented')

########NEW FILE########
__FILENAME__ = key_pairs
from jinja2 import Template
from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.exceptions import InvalidIdError
from moto.ec2.utils import keypair_names_from_querystring, filters_from_querystring


class KeyPairs(BaseResponse):

    def create_key_pair(self):
        try:
            name = self.querystring.get('KeyName')[0]
            keypair = ec2_backend.create_key_pair(name)
        except InvalidIdError as exc:
            template = Template(CREATE_KEY_PAIR_INVALID_NAME)
            return template.render(keypair_id=exc.id), dict(status=400)
        else:
            template = Template(CREATE_KEY_PAIR_RESPONSE)
            return template.render(**keypair)

    def delete_key_pair(self):
        name = self.querystring.get('KeyName')[0]
        success = str(ec2_backend.delete_key_pair(name)).lower()
        return Template(DELETE_KEY_PAIR_RESPONSE).render(success=success)

    def describe_key_pairs(self):
        names = keypair_names_from_querystring(self.querystring)
        filters = filters_from_querystring(self.querystring)
        if len(filters) > 0:
            raise NotImplementedError('Using filters in KeyPairs.describe_key_pairs is not yet implemented')

        try:
            keypairs = ec2_backend.describe_key_pairs(names)
        except InvalidIdError as exc:
            template = Template(CREATE_KEY_PAIR_NOT_FOUND)
            return template.render(keypair_id=exc.id), dict(status=400)
        else:
            template = Template(DESCRIBE_KEY_PAIRS_RESPONSE)
            return template.render(keypairs=keypairs)

    def import_key_pair(self):
        raise NotImplementedError('KeyPairs.import_key_pair is not yet implemented')


DESCRIBE_KEY_PAIRS_RESPONSE = """<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId> 
    <keySet>
    {% for keypair in keypairs %}
      <item>
           <keyName>{{ keypair.name }}</keyName>
           <keyFingerprint>{{ keypair.fingerprint }}</keyFingerprint>
      </item>
    {% endfor %}
    </keySet>
 </DescribeKeyPairsResponse>"""


CREATE_KEY_PAIR_RESPONSE = """<CreateKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <keyName>{{ name }}</keyName>
   <keyFingerprint>
        {{ fingerprint }}
   </keyFingerprint>
   <keyMaterial>{{ material }}
    </keyMaterial>
</CreateKeyPairResponse>"""


CREATE_KEY_PAIR_INVALID_NAME = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>InvalidKeyPair.Duplicate</Code><Message>The keypair '{{ keypair_id }}' already exists.</Message></Error></Errors><RequestID>f4f76e81-8ca5-4e61-a6d5-a4a96EXAMPLE</RequestID></Response>
"""


CREATE_KEY_PAIR_NOT_FOUND = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>InvalidKeyPair.NotFound</Code><Message>The keypair '{{ keypair_id }}' does not exist.</Message></Error></Errors><RequestID>f4f76e81-8ca5-4e61-a6d5-a4a96EXAMPLE</RequestID></Response>
"""


DELETE_KEY_PAIR_RESPONSE = """<DeleteKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId> 
  <return>{{ success }}</return>
</DeleteKeyPairResponse>"""

########NEW FILE########
__FILENAME__ = monitoring
from moto.core.responses import BaseResponse


class Monitoring(BaseResponse):
    def monitor_instances(self):
        raise NotImplementedError('Monitoring.monitor_instances is not yet implemented')

    def unmonitor_instances(self):
        raise NotImplementedError('Monitoring.unmonitor_instances is not yet implemented')

########NEW FILE########
__FILENAME__ = network_acls
from moto.core.responses import BaseResponse


class NetworkACLs(BaseResponse):
    def create_network_acl(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).create_network_acl is not yet implemented')

    def create_network_acl_entry(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).create_network_acl_entry is not yet implemented')

    def delete_network_acl(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).delete_network_acl is not yet implemented')

    def delete_network_acl_entry(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).delete_network_acl_entry is not yet implemented')

    def describe_network_acls(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).describe_network_acls is not yet implemented')

    def replace_network_acl_association(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).replace_network_acl_association is not yet implemented')

    def replace_network_acl_entry(self):
        raise NotImplementedError('NetworkACLs(AmazonVPC).replace_network_acl_entry is not yet implemented')

########NEW FILE########
__FILENAME__ = placement_groups
from moto.core.responses import BaseResponse


class PlacementGroups(BaseResponse):
    def create_placement_group(self):
        raise NotImplementedError('PlacementGroups.create_placement_group is not yet implemented')

    def delete_placement_group(self):
        raise NotImplementedError('PlacementGroups.delete_placement_group is not yet implemented')

    def describe_placement_groups(self):
        raise NotImplementedError('PlacementGroups.describe_placement_groups is not yet implemented')

########NEW FILE########
__FILENAME__ = reserved_instances
from moto.core.responses import BaseResponse


class ReservedInstances(BaseResponse):
    def cancel_reserved_instances_listing(self):
        raise NotImplementedError('ReservedInstances.cancel_reserved_instances_listing is not yet implemented')

    def create_reserved_instances_listing(self):
        raise NotImplementedError('ReservedInstances.create_reserved_instances_listing is not yet implemented')

    def describe_reserved_instances(self):
        raise NotImplementedError('ReservedInstances.describe_reserved_instances is not yet implemented')

    def describe_reserved_instances_listings(self):
        raise NotImplementedError('ReservedInstances.describe_reserved_instances_listings is not yet implemented')

    def describe_reserved_instances_offerings(self):
        raise NotImplementedError('ReservedInstances.describe_reserved_instances_offerings is not yet implemented')

    def purchase_reserved_instances_offering(self):
        raise NotImplementedError('ReservedInstances.purchase_reserved_instances_offering is not yet implemented')

########NEW FILE########
__FILENAME__ = route_tables
from moto.core.responses import BaseResponse


class RouteTables(BaseResponse):
    def associate_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).associate_route_table is not yet implemented')

    def create_route(self):
        raise NotImplementedError('RouteTables(AmazonVPC).create_route is not yet implemented')

    def create_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).create_route_table is not yet implemented')

    def delete_route(self):
        raise NotImplementedError('RouteTables(AmazonVPC).delete_route is not yet implemented')

    def delete_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).delete_route_table is not yet implemented')

    def describe_route_tables(self):
        raise NotImplementedError('RouteTables(AmazonVPC).describe_route_tables is not yet implemented')

    def disassociate_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).disassociate_route_table is not yet implemented')

    def replace_route(self):
        raise NotImplementedError('RouteTables(AmazonVPC).replace_route is not yet implemented')

    def replace_route_table_association(self):
        raise NotImplementedError('RouteTables(AmazonVPC).replace_route_table_association is not yet implemented')

########NEW FILE########
__FILENAME__ = security_groups
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


def process_rules_from_querystring(querystring):

    name = None
    group_id = None

    try:
        name = querystring.get('GroupName')[0]
    except:
        group_id = querystring.get('GroupId')[0]

    ip_protocol = querystring.get('IpPermissions.1.IpProtocol')[0]
    from_port = querystring.get('IpPermissions.1.FromPort')[0]
    to_port = querystring.get('IpPermissions.1.ToPort')[0]
    ip_ranges = []
    for key, value in querystring.iteritems():
        if 'IpPermissions.1.IpRanges' in key:
            ip_ranges.append(value[0])

    source_groups = []
    source_group_ids = []

    for key, value in querystring.iteritems():
        if 'IpPermissions.1.Groups.1.GroupId' in key:
            source_group_ids.append(value[0])
        elif 'IpPermissions.1.Groups' in key:
            source_groups.append(value[0])

    return (name, group_id, ip_protocol, from_port, to_port, ip_ranges, source_groups, source_group_ids)


class SecurityGroups(BaseResponse):
    def authorize_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.authorize_security_group_egress is not yet implemented')

    def authorize_security_group_ingress(self):
        ec2_backend.authorize_security_group_ingress(*process_rules_from_querystring(self.querystring))
        return AUTHORIZE_SECURITY_GROUP_INGRESS_REPONSE

    def create_security_group(self):
        name = self.querystring.get('GroupName')[0]
        try:
            description = self.querystring.get('GroupDescription')[0]
        except TypeError:
            # No description found, return error
            return "The request must contain the parameter GroupDescription", dict(status=400)
        vpc_id = self.querystring.get("VpcId", [None])[0]
        group = ec2_backend.create_security_group(name, description, vpc_id=vpc_id)
        if not group:
            # There was an exisitng group
            return "There was an existing security group with name {0}".format(name), dict(status=409)
        template = Template(CREATE_SECURITY_GROUP_RESPONSE)
        return template.render(group=group)

    def delete_security_group(self):
        # TODO this should raise an error if there are instances in the group. See http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DeleteSecurityGroup.html

        name = self.querystring.get('GroupName')
        sg_id = self.querystring.get('GroupId')

        if name:
            group = ec2_backend.delete_security_group(name[0])
        elif sg_id:
            group = ec2_backend.delete_security_group(group_id=sg_id[0])

        # needs name or group now
        if not group:
            # There was no such group
            return "There was no security group with name {0}".format(name), dict(status=404)
        return DELETE_GROUP_RESPONSE

    def describe_security_groups(self):
        groups = ec2_backend.describe_security_groups()
        template = Template(DESCRIBE_SECURITY_GROUPS_RESPONSE)
        return template.render(groups=groups)

    def revoke_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.revoke_security_group_egress is not yet implemented')

    def revoke_security_group_ingress(self):
        success = ec2_backend.revoke_security_group_ingress(*process_rules_from_querystring(self.querystring))
        if not success:
            return "Could not find a matching ingress rule", dict(status=404)
        return REVOKE_SECURITY_GROUP_INGRESS_REPONSE


CREATE_SECURITY_GROUP_RESPONSE = """<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
   <groupId>{{ group.id }}</groupId>
</CreateSecurityGroupResponse>"""

DELETE_GROUP_RESPONSE = """<DeleteSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSecurityGroupResponse>"""

DESCRIBE_SECURITY_GROUPS_RESPONSE = """<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <securityGroupInfo>
      {% for group in groups %}
          <item>
             <ownerId>111122223333</ownerId>
             <groupId>{{ group.id }}</groupId>
             <groupName>{{ group.name }}</groupName>
             <groupDescription>{{ group.description }}</groupDescription>
             <vpcId>{{ group.vpc_id or ""}}</vpcId>
             <ipPermissions>
               {% for rule in group.ingress_rules %}
                    <item>
                       <ipProtocol>{{ rule.ip_protocol }}</ipProtocol>
                       <fromPort>{{ rule.from_port }}</fromPort>
                       <toPort>{{ rule.to_port }}</toPort>
                       <groups>
                          {% for source_group in rule.source_groups %}
                              <item>
                                 <userId>111122223333</userId>
                                 <groupId>{{ source_group.id }}</groupId>
                                 <groupName>{{ source_group.name }}</groupName>
                              </item>
                          {% endfor %}
                       </groups>
                       <ipRanges>
                          {% for ip_range in rule.ip_ranges %}
                              <item>
                                 <cidrIp>{{ ip_range }}</cidrIp>
                              </item>
                          {% endfor %}
                       </ipRanges>
                    </item>
                {% endfor %}
             </ipPermissions>
             <ipPermissionsEgress/>
          </item>
      {% endfor %}
   </securityGroupInfo>
</DescribeSecurityGroupsResponse>"""

AUTHORIZE_SECURITY_GROUP_INGRESS_REPONSE = """<AuthorizeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</AuthorizeSecurityGroupIngressResponse>"""

REVOKE_SECURITY_GROUP_INGRESS_REPONSE = """<RevokeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RevokeSecurityGroupIngressResponse>"""

########NEW FILE########
__FILENAME__ = spot_instances
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class SpotInstances(BaseResponse):
    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def _get_int_param(self, param_name):
        value = self._get_param(param_name)
        if value is not None:
            return int(value)

    def cancel_spot_instance_requests(self):
        request_ids = self._get_multi_param('SpotInstanceRequestId')
        requests = ec2_backend.cancel_spot_instance_requests(request_ids)
        template = Template(CANCEL_SPOT_INSTANCES_TEMPLATE)
        return template.render(requests=requests)

    def create_spot_datafeed_subscription(self):
        raise NotImplementedError('SpotInstances.create_spot_datafeed_subscription is not yet implemented')

    def delete_spot_datafeed_subscription(self):
        raise NotImplementedError('SpotInstances.delete_spot_datafeed_subscription is not yet implemented')

    def describe_spot_datafeed_subscription(self):
        raise NotImplementedError('SpotInstances.describe_spot_datafeed_subscription is not yet implemented')

    def describe_spot_instance_requests(self):
        requests = ec2_backend.describe_spot_instance_requests()
        template = Template(DESCRIBE_SPOT_INSTANCES_TEMPLATE)
        return template.render(requests=requests)

    def describe_spot_price_history(self):
        raise NotImplementedError('SpotInstances.describe_spot_price_history is not yet implemented')

    def request_spot_instances(self):
        price = self._get_param('SpotPrice')
        image_id = self._get_param('LaunchSpecification.ImageId')
        count = self._get_int_param('InstanceCount')
        type = self._get_param('Type')
        valid_from = self._get_param('ValidFrom')
        valid_until = self._get_param('ValidUntil')
        launch_group = self._get_param('LaunchGroup')
        availability_zone_group = self._get_param('AvailabilityZoneGroup')
        key_name = self._get_param('LaunchSpecification.KeyName')
        security_groups = self._get_multi_param('LaunchSpecification.SecurityGroup')
        user_data = self._get_param('LaunchSpecification.UserData')
        instance_type = self._get_param('LaunchSpecification.InstanceType')
        placement = self._get_param('LaunchSpecification.Placement.AvailabilityZone')
        kernel_id = self._get_param('LaunchSpecification.KernelId')
        ramdisk_id = self._get_param('LaunchSpecification.RamdiskId')
        monitoring_enabled = self._get_param('LaunchSpecification.Monitoring.Enabled')
        subnet_id = self._get_param('LaunchSpecification.SubnetId')

        requests = ec2_backend.request_spot_instances(
            price=price,
            image_id=image_id,
            count=count,
            type=type,
            valid_from=valid_from,
            valid_until=valid_until,
            launch_group=launch_group,
            availability_zone_group=availability_zone_group,
            key_name=key_name,
            security_groups=security_groups,
            user_data=user_data,
            instance_type=instance_type,
            placement=placement,
            kernel_id=kernel_id,
            ramdisk_id=ramdisk_id,
            monitoring_enabled=monitoring_enabled,
            subnet_id=subnet_id,
        )

        template = Template(REQUEST_SPOT_INSTANCES_TEMPLATE)
        return template.render(requests=requests)


REQUEST_SPOT_INSTANCES_TEMPLATE = """<RequestSpotInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2013-06-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <spotInstanceRequestSet>
    {% for request in requests %}
    <item>
      <spotInstanceRequestId>{{ request.id }}</spotInstanceRequestId>
      <spotPrice>{{ request.price }}</spotPrice>
      <type>{{ request.type }}</type>
      <state>{{ request.state }}</state>
      <status>
        <code>pending-evaluation</code>
        <updateTime>YYYY-MM-DDTHH:MM:SS.000Z</updateTime>
        <message>Your Spot request has been submitted for review, and is pending evaluation.</message>
      </status>
      <availabilityZoneGroup>{{ request.availability_zone_group }}</availabilityZoneGroup>
      <launchSpecification>
        <imageId>{{ request.image_id }}</imageId>
        <keyName>{{ request.key_name }}</keyName>
        <groupSet>
          {% for group in request.security_groups %}
          <item>
            <groupId>{{ group.id }}</groupId>
            <groupName>{{ group.name }}</groupName>
          </item>
          {% endfor %}
        </groupSet>
        <kernelId>{{ request.kernel_id }}</kernelId>
        <ramdiskId>{{ request.ramdisk_id }}</ramdiskId>
        <subnetId>{{ request.subnet_id }}</subnetId>
        <instanceType>{{ request.instance_type }}</instanceType>
        <blockDeviceMapping/>
        <monitoring>
          <enabled>{{ request.monitoring_enabled }}</enabled>
        </monitoring>
        <ebsOptimized>{{ request.ebs_optimized }}</ebsOptimized>
        <PlacementRequestType>
          <availabilityZone>{{ request.placement }}</availabilityZone>
          <groupName></groupName>
        </PlacementRequestType>
      </launchSpecification>
      <launchGroup>{{ request.launch_group }}</launchGroup>
      <createTime>YYYY-MM-DDTHH:MM:SS.000Z</createTime>
      {% if request.valid_from %}
      <validFrom>{{ request.valid_from }}</validFrom>
      {% endif %}
      {% if request.valid_until %}
      <validUntil>{{ request.valid_until }}</validUntil>
      {% endif %}
      <productDescription>Linux/UNIX</productDescription>
    </item>
    {% endfor %}
 </spotInstanceRequestSet>
</RequestSpotInstancesResponse>"""

DESCRIBE_SPOT_INSTANCES_TEMPLATE = """<DescribeSpotInstanceRequestsResponse xmlns="http://ec2.amazonaws.com/doc/2013-06-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <spotInstanceRequestSet>
    {% for request in requests %}
    <item>
      <spotInstanceRequestId>{{ request.id }}</spotInstanceRequestId>
      <spotPrice>{{ request.price }}</spotPrice>
      <type>{{ request.type }}</type>
      <state>{{ request.state }}</state>
      <status>
        <code>pending-evaluation</code>
        <updateTime>YYYY-MM-DDTHH:MM:SS.000Z</updateTime>
        <message>Your Spot request has been submitted for review, and is pending evaluation.</message>
      </status>
      {% if request.availability_zone_group %}
        <availabilityZoneGroup>{{ request.availability_zone_group }}</availabilityZoneGroup>
      {% endif %}
      <launchSpecification>
        <imageId>{{ request.image_id }}</imageId>
        {% if request.key_name %}
          <keyName>{{ request.key_name }}</keyName>
        {% endif %}
        <groupSet>
          {% for group in request.security_groups %}
          <item>
            <groupId>{{ group.id }}</groupId>
            <groupName>{{ group.name }}</groupName>
          </item>
          {% endfor %}
        </groupSet>
        {% if request.kernel_id %}
        <kernelId>{{ request.kernel_id }}</kernelId>
        {% endif %}
        {% if request.ramdisk_id %}
        <ramdiskId>{{ request.ramdisk_id }}</ramdiskId>
        {% endif %}
        {% if request.subnet_id %}
        <subnetId>{{ request.subnet_id }}</subnetId>
        {% endif %}
        <instanceType>{{ request.instance_type }}</instanceType>
        <blockDeviceMapping/>
        <monitoring>
          <enabled>{{ request.monitoring_enabled }}</enabled>
        </monitoring>
        <ebsOptimized>{{ request.ebs_optimized }}</ebsOptimized>
        {% if request.placement %}
          <PlacementRequestType>
            <availabilityZone>{{ request.placement }}</availabilityZone>
            <groupName></groupName>
          </PlacementRequestType>
        {% endif %}
      </launchSpecification>
      {% if request.launch_group %}
        <launchGroup>{{ request.launch_group }}</launchGroup>
      {% endif %}
        <createTime>YYYY-MM-DDTHH:MM:SS.000Z</createTime>
      {% if request.valid_from %}
        <validFrom>{{ request.valid_from }}</validFrom>
      {% endif %}
      {% if request.valid_until %}
        <validUntil>{{ request.valid_until }}</validUntil>
      {% endif %}
      <productDescription>Linux/UNIX</productDescription>
    </item>
    {% endfor %}
  </spotInstanceRequestSet>
</DescribeSpotInstanceRequestsResponse>"""

CANCEL_SPOT_INSTANCES_TEMPLATE = """<CancelSpotInstanceRequestsResponse xmlns="http://ec2.amazonaws.com/doc/2013-06-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <spotInstanceRequestSet>
    {% for request in requests %}
    <item>
      <spotInstanceRequestId>{{ request.id }}</spotInstanceRequestId>
      <state>cancelled</state>
    </item>
    {% endfor %}
  </spotInstanceRequestSet>
</CancelSpotInstanceRequestsResponse>"""

########NEW FILE########
__FILENAME__ = subnets
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class Subnets(BaseResponse):
    def create_subnet(self):
        vpc_id = self.querystring.get('VpcId')[0]
        cidr_block = self.querystring.get('CidrBlock')[0]
        subnet = ec2_backend.create_subnet(vpc_id, cidr_block)
        template = Template(CREATE_SUBNET_RESPONSE)
        return template.render(subnet=subnet)

    def delete_subnet(self):
        subnet_id = self.querystring.get('SubnetId')[0]
        subnet = ec2_backend.delete_subnet(subnet_id)
        if subnet:
            template = Template(DELETE_SUBNET_RESPONSE)
            return template.render(subnet=subnet)
        else:
            return "", dict(status=404)

    def describe_subnets(self):
        subnets = ec2_backend.get_all_subnets()
        template = Template(DESCRIBE_SUBNETS_RESPONSE)
        return template.render(subnets=subnets)


CREATE_SUBNET_RESPONSE = """
<CreateSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnet>
    <subnetId>{{ subnet.id }}</subnetId>
    <state>pending</state>
    <vpcId>{{ subnet.vpc_id }}</vpcId>
    <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
    <availableIpAddressCount>251</availableIpAddressCount>
    <availabilityZone>us-east-1a</availabilityZone>
    <tagSet>
      {% for tag in subnet.get_tags() %}
        <item>
          <resourceId>{{ tag.resource_id }}</resourceId>
          <resourceType>{{ tag.resource_type }}</resourceType>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
      {% endfor %}
    </tagSet>
  </subnet>
</CreateSubnetResponse>"""

DELETE_SUBNET_RESPONSE = """
<DeleteSubnetResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteSubnetResponse>"""

DESCRIBE_SUBNETS_RESPONSE = """
<DescribeSubnetsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <subnetSet>
    {% for subnet in subnets %}
      <item>
        <subnetId>{{ subnet.id }}</subnetId>
        <state>available</state>
        <vpcId>{{ subnet.vpc_id }}</vpcId>
        <cidrBlock>{{ subnet.cidr_block }}</cidrBlock>
        <availableIpAddressCount>251</availableIpAddressCount>
        <availabilityZone>us-east-1a</availabilityZone>
        <tagSet>
          {% for tag in subnet.get_tags() %}
            <item>
              <resourceId>{{ tag.resource_id }}</resourceId>
              <resourceType>{{ tag.resource_type }}</resourceType>
              <key>{{ tag.key }}</key>
              <value>{{ tag.value }}</value>
            </item>
          {% endfor %}
        </tagSet>
      </item>
    {% endfor %}
  </subnetSet>
</DescribeSubnetsResponse>"""

########NEW FILE########
__FILENAME__ = tags
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class TagResponse(BaseResponse):

    def create_tags(self):
        resource_ids = resource_ids_from_querystring(self.querystring)
        for resource_id, tag in resource_ids.iteritems():
            ec2_backend.create_tag(resource_id, tag[0], tag[1])
        return CREATE_RESPONSE

    def delete_tags(self):
        resource_ids = resource_ids_from_querystring(self.querystring)
        for resource_id, tag in resource_ids.iteritems():
            ec2_backend.delete_tag(resource_id, tag[0])
        template = Template(DELETE_RESPONSE)
        return template.render(reservations=ec2_backend.all_reservations())

    def describe_tags(self):
        tags = ec2_backend.describe_tags()
        template = Template(DESCRIBE_RESPONSE)
        return template.render(tags=tags)


CREATE_RESPONSE = """<CreateTagsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</CreateTagsResponse>"""

DELETE_RESPONSE = """<DeleteTagsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteTagsResponse>"""

DESCRIBE_RESPONSE = """<DescribeTagsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <tagSet>
      {% for tag in tags %}
          <item>
             <resourceId>{{ tag.resource_id }}</resourceId>
             <resourceType>{{ tag.resource_type }}</resourceType>
             <key>{{ tag.key }}</key>
             <value>{{ tag.value }}</value>
          </item>
      {% endfor %}
    </tagSet>
</DescribeTagsResponse>"""

########NEW FILE########
__FILENAME__ = virtual_private_gateways
from moto.core.responses import BaseResponse


class VirtualPrivateGateways(BaseResponse):
    def attach_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).attach_vpn_gateway is not yet implemented')

    def create_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).create_vpn_gateway is not yet implemented')

    def delete_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).delete_vpn_gateway is not yet implemented')

    def describe_vpn_gateways(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).describe_vpn_gateways is not yet implemented')

    def detach_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).detach_vpn_gateway is not yet implemented')

########NEW FILE########
__FILENAME__ = vm_export
from moto.core.responses import BaseResponse


class VMExport(BaseResponse):
    def cancel_export_task(self):
        raise NotImplementedError('VMExport.cancel_export_task is not yet implemented')

    def create_instance_export_task(self):
        raise NotImplementedError('VMExport.create_instance_export_task is not yet implemented')

    def describe_export_tasks(self):
        raise NotImplementedError('VMExport.describe_export_tasks is not yet implemented')

########NEW FILE########
__FILENAME__ = vm_import
from moto.core.responses import BaseResponse


class VMImport(BaseResponse):
    def cancel_conversion_task(self):
        raise NotImplementedError('VMImport.cancel_conversion_task is not yet implemented')

    def describe_conversion_tasks(self):
        raise NotImplementedError('VMImport.describe_conversion_tasks is not yet implemented')

    def import_instance(self):
        raise NotImplementedError('VMImport.import_instance is not yet implemented')

    def import_volume(self):
        raise NotImplementedError('VMImport.import_volume is not yet implemented')

########NEW FILE########
__FILENAME__ = vpcs
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class VPCs(BaseResponse):
    def create_vpc(self):
        cidr_block = self.querystring.get('CidrBlock')[0]
        vpc = ec2_backend.create_vpc(cidr_block)
        template = Template(CREATE_VPC_RESPONSE)
        return template.render(vpc=vpc)

    def delete_vpc(self):
        vpc_id = self.querystring.get('VpcId')[0]
        vpc = ec2_backend.delete_vpc(vpc_id)
        if vpc:
            template = Template(DELETE_VPC_RESPONSE)
            return template.render(vpc=vpc)
        else:
            return "", dict(status=404)

    def describe_vpcs(self):
        vpcs = ec2_backend.get_all_vpcs()
        template = Template(DESCRIBE_VPCS_RESPONSE)
        return template.render(vpcs=vpcs)


CREATE_VPC_RESPONSE = """
<CreateVpcResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <vpc>
      <vpcId>{{ vpc.id }}</vpcId>
      <state>pending</state>
      <cidrBlock>{{ vpc.cidr_block }}</cidrBlock>
      <dhcpOptionsId>dopt-1a2b3c4d2</dhcpOptionsId>
      <instanceTenancy>default</instanceTenancy>
      <tagSet>
        {% for tag in vpc.get_tags() %}
          <item>
            <resourceId>{{ tag.resource_id }}</resourceId>
            <resourceType>{{ tag.resource_type }}</resourceType>
            <key>{{ tag.key }}</key>
            <value>{{ tag.value }}</value>
          </item>
        {% endfor %}
      </tagSet>
   </vpc>
</CreateVpcResponse>"""

DESCRIBE_VPCS_RESPONSE = """
<DescribeVpcsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <vpcSet>
    {% for vpc in vpcs %}
      <item>
        <vpcId>{{ vpc.id }}</vpcId>
        <state>available</state>
        <cidrBlock>{{ vpc.cidr_block }}</cidrBlock>
        <dhcpOptionsId>dopt-7a8b9c2d</dhcpOptionsId>
        <instanceTenancy>default</instanceTenancy>
        <tagSet>
          {% for tag in vpc.get_tags() %}
            <item>
              <resourceId>{{ tag.resource_id }}</resourceId>
              <resourceType>{{ tag.resource_type }}</resourceType>
              <key>{{ tag.key }}</key>
              <value>{{ tag.value }}</value>
            </item>
          {% endfor %}
        </tagSet>
      </item>
    {% endfor %}
  </vpcSet>
</DescribeVpcsResponse>"""

DELETE_VPC_RESPONSE = """
<DeleteVpcResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteVpcResponse>
"""

########NEW FILE########
__FILENAME__ = vpn_connections
from moto.core.responses import BaseResponse


class VPNConnections(BaseResponse):
    def create_vpn_connection(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).create_vpn_connection is not yet implemented')

    def delete_vpn_connection(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).delete_vpn_connection is not yet implemented')

    def describe_vpn_connections(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).describe_vpn_connections is not yet implemented')

########NEW FILE########
__FILENAME__ = windows
from moto.core.responses import BaseResponse


class Windows(BaseResponse):
    def bundle_instance(self):
        raise NotImplementedError('Windows.bundle_instance is not yet implemented')

    def cancel_bundle_task(self):
        raise NotImplementedError('Windows.cancel_bundle_task is not yet implemented')

    def describe_bundle_tasks(self):
        raise NotImplementedError('Windows.describe_bundle_tasks is not yet implemented')

    def get_password_data(self):
        raise NotImplementedError('Windows.get_password_data is not yet implemented')

########NEW FILE########
__FILENAME__ = urls
from .responses import EC2Response


url_bases = [
    "https?://ec2.(.+).amazonaws.com",
]

url_paths = {
    '{0}/': EC2Response().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import random
import re


def random_id(prefix=''):
    size = 8
    chars = range(10) + ['a', 'b', 'c', 'd', 'e', 'f']

    instance_tag = ''.join(unicode(random.choice(chars)) for x in range(size))
    return '{0}-{1}'.format(prefix, instance_tag)


def random_ami_id():
    return random_id(prefix='ami')


def random_instance_id():
    return random_id(prefix='i')


def random_reservation_id():
    return random_id(prefix='r')


def random_security_group_id():
    return random_id(prefix='sg')


def random_snapshot_id():
    return random_id(prefix='snap')


def random_spot_request_id():
    return random_id(prefix='sir')


def random_subnet_id():
    return random_id(prefix='subnet')


def random_volume_id():
    return random_id(prefix='vol')


def random_vpc_id():
    return random_id(prefix='vpc')


def random_eip_association_id():
    return random_id(prefix='eipassoc')


def random_gateway_id():
    return random_id(prefix='igw')


def random_route_table_id():
    return random_id(prefix='rtb')


def random_eip_allocation_id():
    return random_id(prefix='eipalloc')


def random_dhcp_option_id():
    return random_id(prefix='dopt')


def random_ip():
    return "127.{0}.{1}.{2}".format(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )


def instance_ids_from_querystring(querystring_dict):
    instance_ids = []
    for key, value in querystring_dict.iteritems():
        if 'InstanceId' in key:
            instance_ids.append(value[0])
    return instance_ids


def image_ids_from_querystring(querystring_dict):
    image_ids = []
    for key, value in querystring_dict.iteritems():
        if 'ImageId' in key:
            image_ids.append(value[0])
    return image_ids


def sequence_from_querystring(parameter, querystring_dict):
    parameter_values = []
    for key, value in querystring_dict.iteritems():
        if parameter in key:
            parameter_values.append(value[0])
    return parameter_values


def resource_ids_from_querystring(querystring_dict):
    prefix = 'ResourceId'
    response_values = {}
    for key, value in querystring_dict.iteritems():
        if key.startswith(prefix):
            resource_index = key.replace(prefix + ".", "")
            tag_key = querystring_dict.get("Tag.{0}.Key".format(resource_index))[0]

            tag_value_key = "Tag.{0}.Value".format(resource_index)
            if tag_value_key in querystring_dict:
                tag_value = querystring_dict.get(tag_value_key)[0]
            else:
                tag_value = None
            response_values[value[0]] = (tag_key, tag_value)

    return response_values


def dhcp_configuration_from_querystring(querystring, option=u'DhcpConfiguration'):
    """
    turn:
        {u'AWSAccessKeyId': [u'the_key'],
         u'Action': [u'CreateDhcpOptions'],
         u'DhcpConfiguration.1.Key': [u'domain-name'],
         u'DhcpConfiguration.1.Value.1': [u'example.com'],
         u'DhcpConfiguration.2.Key': [u'domain-name-servers'],
         u'DhcpConfiguration.2.Value.1': [u'10.0.0.6'],
         u'DhcpConfiguration.2.Value.2': [u'10.0.0.7'],
         u'Signature': [u'uUMHYOoLM6r+sT4fhYjdNT6MHw22Wj1mafUpe0P0bY4='],
         u'SignatureMethod': [u'HmacSHA256'],
         u'SignatureVersion': [u'2'],
         u'Timestamp': [u'2014-03-18T21:54:01Z'],
         u'Version': [u'2013-10-15']}
    into:
        {u'domain-name': [u'example.com'], u'domain-name-servers': [u'10.0.0.6', u'10.0.0.7']}
    """

    key_needle = re.compile(u'{0}.[0-9]+.Key'.format(option), re.UNICODE)
    response_values = {}

    for key, value in querystring.iteritems():
        if key_needle.match(key):
            values = []
            key_index = key.split(".")[1]
            value_index = 1
            while True:
                value_key = u'{0}.{1}.Value.{2}'.format(option, key_index, value_index)
                if value_key in querystring:
                    values.extend(querystring[value_key])
                else:
                    break
                value_index += 1
            response_values[value[0]] = values
    return response_values


def filters_from_querystring(querystring_dict):
    response_values = {}
    for key, value in querystring_dict.iteritems():
        match = re.search("Filter.(\d).Name", key)
        if match:
            filter_index = match.groups()[0]
            value_prefix = "Filter.{0}.Value".format(filter_index)
            filter_values = [filter_value[0] for filter_key, filter_value in querystring_dict.iteritems() if filter_key.startswith(value_prefix)]
            response_values[value[0]] = filter_values
    return response_values


def keypair_names_from_querystring(querystring_dict):
    keypair_names = []
    for key, value in querystring_dict.iteritems():
        if 'KeyName' in key:
            keypair_names.append(value[0])
    return keypair_names


filter_dict_attribute_mapping = {
    'instance-state-name': 'state'
}


def passes_filter_dict(instance, filter_dict):
    for filter_name, filter_values in filter_dict.iteritems():
        if filter_name in filter_dict_attribute_mapping:
            instance_attr = filter_dict_attribute_mapping[filter_name]
        else:
            raise NotImplementedError("Filter dicts have not been implemented in Moto for '%s' yet. Feel free to open an issue at https://github.com/spulec/moto/issues", filter_name)
        instance_value = getattr(instance, instance_attr)
        if instance_value not in filter_values:
            return False
    return True


def filter_reservations(reservations, filter_dict):
    result = []
    for reservation in reservations:
        new_instances = []
        for instance in reservation.instances:
            if passes_filter_dict(instance, filter_dict):
                new_instances.append(instance)
        if new_instances:
            reservation.instances = new_instances
            result.append(reservation)
    return result


# not really random ( http://xkcd.com/221/ )
def random_key_pair():
    return {
        'fingerprint': ('1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:'
                        '7d:b8:ca:9f:f5:f1:6f'),
        'material': """---- BEGIN RSA PRIVATE KEY ----
MIICiTCCAfICCQD6m7oRw0uXOjANBgkqhkiG9w0BAQUFADCBiDELMAkGA1UEBhMC
VVMxCzAJBgNVBAgTAldBMRAwDgYDVQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6
b24xFDASBgNVBAsTC0lBTSBDb25zb2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAd
BgkqhkiG9w0BCQEWEG5vb25lQGFtYXpvbi5jb20wHhcNMTEwNDI1MjA0NTIxWhcN
MTIwNDI0MjA0NTIxWjCBiDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAldBMRAwDgYD
VQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6b24xFDASBgNVBAsTC0lBTSBDb25z
b2xlMRIwEAYDVQQDEwlUZXN0Q2lsYWMxHzAdBgkqhkiG9w0BCQEWEG5vb25lQGFt
YXpvbi5jb20wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMaK0dn+a4GmWIWJ
21uUSfwfEvySWtC2XADZ4nB+BLYgVIk60CpiwsZ3G93vUEIO3IyNoH/f0wYK8m9T
rDHudUZg3qX4waLG5M43q7Wgc/MbQITxOUSQv7c7ugFFDzQGBzZswY6786m86gpE
Ibb3OhjZnzcvQAaRHhdlQWIMm2nrAgMBAAEwDQYJKoZIhvcNAQEFBQADgYEAtCu4
nUhVVxYUntneD9+h8Mg9q6q+auNKyExzyLwaxlAoo7TJHidbtS4J5iNmZgXL0Fkb
FFBjvSfpJIlJ00zbhNYS5f6GuoEDmFJl0ZxBHjJnyp378OD8uTs7fLvjx79LjSTb
NYiytVbZPQUQ5Yaxu2jXnimvw3rrszlaEXAMPLE
-----END RSA PRIVATE KEY-----"""
    }

########NEW FILE########
__FILENAME__ = models
from moto.core import BaseBackend


class FakeHealthCheck(object):
    def __init__(self, timeout, healthy_threshold, unhealthy_threshold,
                 interval, target):
        self.timeout = timeout
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.interval = interval
        self.target = target


class FakeListener(object):
    def __init__(self, load_balancer_port, instance_port, protocol):
        self.load_balancer_port = load_balancer_port
        self.instance_port = instance_port
        self.protocol = protocol.upper()


class FakeLoadBalancer(object):
    def __init__(self, name, zones, ports):
        self.name = name
        self.health_check = None
        self.instance_ids = []
        self.zones = zones
        self.listeners = []
        for protocol, lb_port, instance_port in ports:
            listener = FakeListener(
                protocol=protocol,
                load_balancer_port=lb_port,
                instance_port=instance_port,
            )
            self.listeners.append(listener)

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        new_elb = elb_backend.create_load_balancer(
            name=properties.get('LoadBalancerName', resource_name),
            zones=properties.get('AvailabilityZones'),
            ports=[],
        )

        instance_ids = cloudformation_json.get('Instances', [])
        for instance_id in instance_ids:
            elb_backend.register_instances(new_elb.name, [instance_id])
        return new_elb

    @property
    def physical_resource_id(self):
        return self.name


class ELBBackend(BaseBackend):

    def __init__(self):
        self.load_balancers = {}

    def create_load_balancer(self, name, zones, ports):
        new_load_balancer = FakeLoadBalancer(name=name, zones=zones, ports=ports)
        self.load_balancers[name] = new_load_balancer
        return new_load_balancer

    def describe_load_balancers(self, names):
        balancers = self.load_balancers.values()
        if names:
            return [balancer for balancer in balancers if balancer.name in names]
        else:
            return balancers

    def delete_load_balancer(self, load_balancer_name):
        self.load_balancers.pop(load_balancer_name, None)

    def get_load_balancer(self, load_balancer_name):
        return self.load_balancers.get(load_balancer_name)

    def configure_health_check(self, load_balancer_name, timeout,
                               healthy_threshold, unhealthy_threshold, interval,
                               target):
        check = FakeHealthCheck(timeout, healthy_threshold, unhealthy_threshold,
                                interval, target)
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.health_check = check
        return check

    def register_instances(self, load_balancer_name, instance_ids):
        load_balancer = self.get_load_balancer(load_balancer_name)
        load_balancer.instance_ids.extend(instance_ids)
        return load_balancer

    def deregister_instances(self, load_balancer_name, instance_ids):
        load_balancer = self.get_load_balancer(load_balancer_name)
        new_instance_ids = [instance_id for instance_id in load_balancer.instance_ids if instance_id not in instance_ids]
        load_balancer.instance_ids = new_instance_ids
        return load_balancer

elb_backend = ELBBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import elb_backend


class ELBResponse(BaseResponse):

    def create_load_balancer(self):
        """
        u'Scheme': [u'internet-facing'],
        """
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        availability_zones = [value[0] for key, value in self.querystring.items() if "AvailabilityZones.member" in key]
        ports = []
        port_index = 1
        while True:
            try:
                protocol = self.querystring['Listeners.member.{0}.Protocol'.format(port_index)][0]
            except KeyError:
                break
            lb_port = self.querystring['Listeners.member.{0}.LoadBalancerPort'.format(port_index)][0]
            instance_port = self.querystring['Listeners.member.{0}.InstancePort'.format(port_index)][0]
            ports.append([protocol, lb_port, instance_port])
            port_index += 1
        elb_backend.create_load_balancer(
            name=load_balancer_name,
            zones=availability_zones,
            ports=ports,
        )
        template = Template(CREATE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def describe_load_balancers(self):
        names = [value[0] for key, value in self.querystring.items() if "LoadBalancerNames.member" in key]
        load_balancers = elb_backend.describe_load_balancers(names)
        template = Template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers)

    def delete_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        elb_backend.delete_load_balancer(load_balancer_name)
        template = Template(DELETE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def configure_health_check(self):
        check = elb_backend.configure_health_check(
            load_balancer_name=self.querystring.get('LoadBalancerName')[0],
            timeout=self.querystring.get('HealthCheck.Timeout')[0],
            healthy_threshold=self.querystring.get('HealthCheck.HealthyThreshold')[0],
            unhealthy_threshold=self.querystring.get('HealthCheck.UnhealthyThreshold')[0],
            interval=self.querystring.get('HealthCheck.Interval')[0],
            target=self.querystring.get('HealthCheck.Target')[0],
        )
        template = Template(CONFIGURE_HEALTH_CHECK_TEMPLATE)
        return template.render(check=check)

    def register_instances_with_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        template = Template(REGISTER_INSTANCES_TEMPLATE)
        load_balancer = elb_backend.register_instances(load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

    def deregister_instances_from_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        template = Template(DEREGISTER_INSTANCES_TEMPLATE)
        load_balancer = elb_backend.deregister_instances(load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

CREATE_LOAD_BALANCER_TEMPLATE = """<CreateLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <DNSName>tests.us-east-1.elb.amazonaws.com</DNSName>
</CreateLoadBalancerResult>"""

DELETE_LOAD_BALANCER_TEMPLATE = """<DeleteLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
</DeleteLoadBalancerResult>"""

DESCRIBE_LOAD_BALANCERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancersResult>
    <LoadBalancerDescriptions>
      {% for load_balancer in load_balancers %}
        <member>
          <SecurityGroups>
          </SecurityGroups>
          <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
          <CreatedTime>2013-01-01T00:00:00.19000Z</CreatedTime>
          <HealthCheck>
            {% if load_balancer.health_check %}
              <Interval>{{ load_balancer.health_check.interval }}</Interval>
              <Target>{{ load_balancer.health_check.target }}</Target>
              <HealthyThreshold>{{ load_balancer.health_check.healthy_threshold }}</HealthyThreshold>
              <Timeout>{{ load_balancer.health_check.timeout }}</Timeout>
              <UnhealthyThreshold>{{ load_balancer.health_check.unhealthy_threshold }}</UnhealthyThreshold>
            {% endif %}
          </HealthCheck>
          <VPCId>vpc-56e10e3d</VPCId>
          <ListenerDescriptions>
            {% for listener in load_balancer.listeners %}
              <member>
                <PolicyNames>
                  <member>AWSConsolePolicy-1</member>
                </PolicyNames>
                <Listener>
                  <Protocol>{{ listener.protocol }}</Protocol>
                  <LoadBalancerPort>{{ listener.load_balancer_port }}</LoadBalancerPort>
                  <InstanceProtocol>{{ listener.protocol }}</InstanceProtocol>
                  <InstancePort>{{ listener.instance_port }}</InstancePort>
                </Listener>
              </member>
            {% endfor %}
          </ListenerDescriptions>
          <Instances>
            {% for instance_id in load_balancer.instance_ids %}
              <member>
                <InstanceId>{{ instance_id }}</InstanceId>
              </member>
            {% endfor %}
          </Instances>
          <Policies>
            <AppCookieStickinessPolicies/>
            <OtherPolicies/>
            <LBCookieStickinessPolicies>
              <member>
                <PolicyName>AWSConsolePolicy-1</PolicyName>
                <CookieExpirationPeriod>30</CookieExpirationPeriod>
              </member>
            </LBCookieStickinessPolicies>
          </Policies>
          <AvailabilityZones>
            {% for zone in load_balancer.zones %}
              <member>{{ zone }}</member>
            {% endfor %}
          </AvailabilityZones>
          <CanonicalHostedZoneName>tests.us-east-1.elb.amazonaws.com</CanonicalHostedZoneName>
          <CanonicalHostedZoneNameID>Z3ZONEID</CanonicalHostedZoneNameID>
          <Scheme>internet-facing</Scheme>
          <DNSName>tests.us-east-1.elb.amazonaws.com</DNSName>
          <BackendServerDescriptions/>
          <Subnets>
          </Subnets>
        </member>
      {% endfor %}
    </LoadBalancerDescriptions>
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>"""

CONFIGURE_HEALTH_CHECK_TEMPLATE = """<ConfigureHealthCheckResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <HealthCheck>
    <Interval>{{ check.interval }}</Interval>
    <Target>{{ check.target }}</Target>
    <HealthyThreshold>{{ check.healthy_threshold }}</HealthyThreshold>
    <Timeout>{{ check.timeout }}</Timeout>
    <UnhealthyThreshold>{{ check.unhealthy_threshold }}</UnhealthyThreshold>
  </HealthCheck>
</ConfigureHealthCheckResult>"""

REGISTER_INSTANCES_TEMPLATE = """<RegisterInstancesWithLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <Instances>
    {% for instance_id in load_balancer.instance_ids %}
      <member>
        <InstanceId>{{ instance_id }}</InstanceId>
      </member>
    {% endfor %}
  </Instances>
</RegisterInstancesWithLoadBalancerResult>"""

DEREGISTER_INSTANCES_TEMPLATE = """<DeregisterInstancesWithLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <Instances>
    {% for instance_id in load_balancer.instance_ids %}
      <member>
        <InstanceId>{{ instance_id }}</InstanceId>
      </member>
    {% endfor %}
  </Instances>
</DeregisterInstancesWithLoadBalancerResult>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import ELBResponse

url_bases = [
    "https?://elasticloadbalancing.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': ELBResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = models
from moto.core import BaseBackend

from .utils import random_job_id, random_instance_group_id

DEFAULT_JOB_FLOW_ROLE = 'EMRJobflowDefault'


class FakeInstanceGroup(object):
    def __init__(self, id, instance_count, instance_role, instance_type, market, name, bid_price=None):
        self.id = id
        self.num_instances = instance_count
        self.role = instance_role
        self.type = instance_type
        self.market = market
        self.name = name
        self.bid_price = bid_price

    def set_instance_count(self, instance_count):
        self.num_instances = instance_count


class FakeStep(object):
    def __init__(self, state, **kwargs):
        # 'Steps.member.1.HadoopJarStep.Jar': ['/home/hadoop/contrib/streaming/hadoop-streaming.jar'],
        # 'Steps.member.1.HadoopJarStep.Args.member.1': ['-mapper'],
        # 'Steps.member.1.HadoopJarStep.Args.member.2': ['s3n://elasticmapreduce/samples/wordcount/wordSplitter.py'],
        # 'Steps.member.1.HadoopJarStep.Args.member.3': ['-reducer'],
        # 'Steps.member.1.HadoopJarStep.Args.member.4': ['aggregate'],
        # 'Steps.member.1.HadoopJarStep.Args.member.5': ['-input'],
        # 'Steps.member.1.HadoopJarStep.Args.member.6': ['s3n://elasticmapreduce/samples/wordcount/input'],
        # 'Steps.member.1.HadoopJarStep.Args.member.7': ['-output'],
        # 'Steps.member.1.HadoopJarStep.Args.member.8': ['s3n://<my output bucket>/output/wordcount_output'],
        # 'Steps.member.1.ActionOnFailure': ['TERMINATE_JOB_FLOW'],
        # 'Steps.member.1.Name': ['My wordcount example']}

        self.action_on_failure = kwargs['action_on_failure']
        self.name = kwargs['name']
        self.jar = kwargs['hadoop_jar_step._jar']
        self.args = []
        self.state = state

        arg_index = 1
        while True:
            arg = kwargs.get('hadoop_jar_step._args.member.{0}'.format(arg_index))
            if arg:
                self.args.append(arg)
                arg_index += 1
            else:
                break


class FakeJobFlow(object):
    def __init__(self, job_id, name, log_uri, job_flow_role, visible_to_all_users, steps, instance_attrs):
        self.id = job_id
        self.name = name
        self.log_uri = log_uri
        self.role = job_flow_role or DEFAULT_JOB_FLOW_ROLE
        self.state = "STARTING"
        self.steps = []
        self.add_steps(steps)

        self.initial_instance_count = instance_attrs.get('instance_count', 0)
        self.initial_master_instance_type = instance_attrs.get('master_instance_type')
        self.initial_slave_instance_type = instance_attrs.get('slave_instance_type')

        self.set_visibility(visible_to_all_users)
        self.normalized_instance_hours = 0
        self.ec2_key_name = instance_attrs.get('ec2_key_name')
        self.availability_zone = instance_attrs.get('placement.availability_zone')
        self.keep_job_flow_alive_when_no_steps = instance_attrs.get('keep_job_flow_alive_when_no_steps')
        self.termination_protected = instance_attrs.get('termination_protected')

        self.instance_group_ids = []

    def terminate(self):
        self.state = 'TERMINATED'

    def set_visibility(self, visibility):
        if visibility == 'true':
            self.visible_to_all_users = True
        else:
            self.visible_to_all_users = False

    def add_steps(self, steps):
        for index, step in enumerate(steps):
            if self.steps:
                # If we already have other steps, this one is pending
                self.steps.append(FakeStep(state='PENDING', **step))
            else:
                self.steps.append(FakeStep(state='STARTING', **step))

    def add_instance_group(self, instance_group_id):
        self.instance_group_ids.append(instance_group_id)

    @property
    def instance_groups(self):
        return emr_backend.get_instance_groups(self.instance_group_ids)

    @property
    def master_instance_type(self):
        groups = self.instance_groups
        if groups:
            return groups[0].type
        else:
            return self.initial_master_instance_type

    @property
    def slave_instance_type(self):
        groups = self.instance_groups
        if groups:
            return groups[0].type
        else:
            return self.initial_slave_instance_type

    @property
    def instance_count(self):
        groups = self.instance_groups
        if not groups:
            # No groups,return initial instance count
            return self.initial_instance_count
        count = 0
        for group in groups:
            count += int(group.num_instances)
        return count


class ElasticMapReduceBackend(BaseBackend):

    def __init__(self):
        self.job_flows = {}
        self.instance_groups = {}

    def run_job_flow(self, name, log_uri, job_flow_role, visible_to_all_users, steps, instance_attrs):
        job_id = random_job_id()
        job_flow = FakeJobFlow(job_id, name, log_uri, job_flow_role, visible_to_all_users, steps, instance_attrs)
        self.job_flows[job_id] = job_flow
        return job_flow

    def add_job_flow_steps(self, job_flow_id, steps):
        job_flow = self.job_flows[job_flow_id]
        job_flow.add_steps(steps)
        return job_flow

    def describe_job_flows(self):
        return self.job_flows.values()

    def terminate_job_flows(self, job_ids):
        flows = [flow for flow in self.describe_job_flows() if flow.id in job_ids]
        for flow in flows:
            flow.terminate()
        return flows

    def get_instance_groups(self, instance_group_ids):
        return [
            group for group_id, group
            in self.instance_groups.items()
            if group_id in instance_group_ids
        ]

    def add_instance_groups(self, job_flow_id, instance_groups):
        job_flow = self.job_flows[job_flow_id]
        result_groups = []
        for instance_group in instance_groups:
            instance_group_id = random_instance_group_id()
            group = FakeInstanceGroup(instance_group_id, **instance_group)
            self.instance_groups[instance_group_id] = group
            job_flow.add_instance_group(instance_group_id)
            result_groups.append(group)
        return result_groups

    def modify_instance_groups(self, instance_groups):
        result_groups = []
        for instance_group in instance_groups:
            group = self.instance_groups[instance_group['instance_group_id']]
            group.set_instance_count(instance_group['instance_count'])
        return result_groups

    def set_visible_to_all_users(self, job_ids, visible_to_all_users):
        for job_id in job_ids:
            job = self.job_flows[job_id]
            job.set_visibility(visible_to_all_users)


emr_backend = ElasticMapReduceBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import emr_backend


class ElasticMapReduceResponse(BaseResponse):

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def _get_multi_param(self, param_prefix):
        return [value[0] for key, value in self.querystring.items() if key.startswith(param_prefix)]

    def _get_dict_param(self, param_prefix):
        params = {}
        for key, value in self.querystring.items():
            if key.startswith(param_prefix):
                params[camelcase_to_underscores(key.replace(param_prefix, ""))] = value[0]
        return params

    def _get_list_prefix(self, param_prefix):
        results = []
        param_index = 1
        while True:
            index_prefix = "{0}.{1}.".format(param_prefix, param_index)
            new_items = {}
            for key, value in self.querystring.items():
                if key.startswith(index_prefix):
                    new_items[camelcase_to_underscores(key.replace(index_prefix, ""))] = value[0]
            if not new_items:
                break
            results.append(new_items)
            param_index += 1
        return results

    def add_job_flow_steps(self):
        job_flow_id = self._get_param('JobFlowId')
        steps = self._get_list_prefix('Steps.member')

        job_flow = emr_backend.add_job_flow_steps(job_flow_id, steps)
        template = Template(ADD_JOB_FLOW_STEPS_TEMPLATE)
        return template.render(job_flow=job_flow)

    def run_job_flow(self):
        flow_name = self._get_param('Name')
        log_uri = self._get_param('LogUri')
        steps = self._get_list_prefix('Steps.member')
        instance_attrs = self._get_dict_param('Instances.')
        job_flow_role = self._get_param('JobFlowRole')
        visible_to_all_users = self._get_param('VisibleToAllUsers')

        job_flow = emr_backend.run_job_flow(
            flow_name, log_uri, job_flow_role,
            visible_to_all_users, steps, instance_attrs
        )
        template = Template(RUN_JOB_FLOW_TEMPLATE)
        return template.render(job_flow=job_flow)

    def describe_job_flows(self):
        job_flows = emr_backend.describe_job_flows()
        template = Template(DESCRIBE_JOB_FLOWS_TEMPLATE)
        return template.render(job_flows=job_flows)

    def terminate_job_flows(self):
        job_ids = self._get_multi_param('JobFlowIds.member.')
        job_flows = emr_backend.terminate_job_flows(job_ids)
        template = Template(TERMINATE_JOB_FLOWS_TEMPLATE)
        return template.render(job_flows=job_flows)

    def add_instance_groups(self):
        jobflow_id = self._get_param('JobFlowId')
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        instance_groups = emr_backend.add_instance_groups(jobflow_id, instance_groups)
        template = Template(ADD_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    def modify_instance_groups(self):
        instance_groups = self._get_list_prefix('InstanceGroups.member')
        instance_groups = emr_backend.modify_instance_groups(instance_groups)
        template = Template(MODIFY_INSTANCE_GROUPS_TEMPLATE)
        return template.render(instance_groups=instance_groups)

    def set_visible_to_all_users(self):
        visible_to_all_users = self._get_param('VisibleToAllUsers')
        job_ids = self._get_multi_param('JobFlowIds.member')
        emr_backend.set_visible_to_all_users(job_ids, visible_to_all_users)
        template = Template(SET_VISIBLE_TO_ALL_USERS_TEMPLATE)
        return template.render()


RUN_JOB_FLOW_TEMPLATE = """<RunJobFlowResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <RunJobFlowResult>
      <JobFlowId>{{ job_flow.id }}</JobFlowId>
   </RunJobFlowResult>
   <ResponseMetadata>
      <RequestId>
         8296d8b8-ed85-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</RunJobFlowResponse>"""

DESCRIBE_JOB_FLOWS_TEMPLATE = """<DescribeJobFlowsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <DescribeJobFlowsResult>
      <JobFlows>
         {% for job_flow in job_flows %}
         <member>
            <ExecutionStatusDetail>
               <CreationDateTime>2009-01-28T21:49:16Z</CreationDateTime>
               <StartDateTime>2009-01-28T21:49:16Z</StartDateTime>
               <State>{{ job_flow.state }}</State>
            </ExecutionStatusDetail>
            <Name>{{ job_flow.name }}</Name>
            <JobFlowRole>{{ job_flow.role }}</JobFlowRole>
            <LogUri>{{ job_flow.log_uri }}</LogUri>
            <Steps>
               {% for step in job_flow.steps %}
               <member>
                  <ExecutionStatusDetail>
                     <CreationDateTime>2009-01-28T21:49:16Z</CreationDateTime>
                     <State>{{ step.state }}</State>
                  </ExecutionStatusDetail>
                  <StepConfig>
                     <HadoopJarStep>
                        <Jar>{{ step.jar }}</Jar>
                        <MainClass>MyMainClass</MainClass>
                        <Args>
                           {% for arg in step.args %}
                           <member>{{ arg }}</member>
                           {% endfor %}
                        </Args>
                        <Properties/>
                     </HadoopJarStep>
                     <Name>{{ step.name }}</Name>
                     <ActionOnFailure>CONTINUE</ActionOnFailure>
                  </StepConfig>
               </member>
               {% endfor %}
            </Steps>
            <JobFlowId>{{ job_flow.id }}</JobFlowId>
            <Instances>
               <Placement>
                  <AvailabilityZone>us-east-1a</AvailabilityZone>
               </Placement>
               <SlaveInstanceType>{{ job_flow.slave_instance_type }}</SlaveInstanceType>
               <MasterInstanceType>{{ job_flow.master_instance_type }}</MasterInstanceType>
               <Ec2KeyName>{{ job_flow.ec2_key_name }}</Ec2KeyName>
               <NormalizedInstanceHours>{{ job_flow.normalized_instance_hours }}</NormalizedInstanceHours>
               <VisibleToAllUsers>{{ job_flow.visible_to_all_users }}</VisibleToAllUsers>
               <InstanceCount>{{ job_flow.instance_count }}</InstanceCount>
               <KeepJobFlowAliveWhenNoSteps>{{ job_flow.keep_job_flow_alive_when_no_steps }}</KeepJobFlowAliveWhenNoSteps>
               <TerminationProtected>{{ job_flow.termination_protected }}</TerminationProtected>
               <InstanceGroups>
                  {% for instance_group in job_flow.instance_groups %}
                  <member>
                    <InstanceGroupId>{{ instance_group.id }}</InstanceGroupId>
                    <InstanceRole>{{ instance_group.role }}</InstanceRole>
                    <InstanceRunningCount>{{ instance_group.num_instances }}</InstanceRunningCount>
                    <InstanceType>{{ instance_group.type }}</InstanceType>
                    <Market>{{ instance_group.market }}</Market>
                    <Name>{{ instance_group.name }}</Name>
                    <BidPrice>{{ instance_group.bid_price }}</BidPrice>
                  </member>
                  {% endfor %}
               </InstanceGroups>
            </Instances>
         </member>
         {% endfor %}
      </JobFlows>
   </DescribeJobFlowsResult>
   <ResponseMetadata>
      <RequestId>
         9cea3229-ed85-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</DescribeJobFlowsResponse>"""

TERMINATE_JOB_FLOWS_TEMPLATE = """<TerminateJobFlowsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</TerminateJobFlowsResponse>"""

ADD_JOB_FLOW_STEPS_TEMPLATE = """<AddJobFlowStepsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         df6f4f4a-ed85-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</AddJobFlowStepsResponse>"""

ADD_INSTANCE_GROUPS_TEMPLATE = """<AddInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <InstanceGroupIds>{% for instance_group in instance_groups %}{{ instance_group.id }}{% if loop.index != loop.length %},{% endif %}{% endfor %}</InstanceGroupIds>
</AddInstanceGroupsResponse>"""

MODIFY_INSTANCE_GROUPS_TEMPLATE = """<ModifyInstanceGroupsResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</ModifyInstanceGroupsResponse>"""

SET_VISIBLE_TO_ALL_USERS_TEMPLATE = """<SetVisibleToAllUsersResponse xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</SetVisibleToAllUsersResponse>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import ElasticMapReduceResponse

url_bases = [
    "https?://elasticmapreduce.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': ElasticMapReduceResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import random
import string


def random_job_id(size=13):
    chars = range(10) + list(string.uppercase)
    job_tag = ''.join(unicode(random.choice(chars)) for x in range(size))
    return 'j-{0}'.format(job_tag)


def random_instance_group_id(size=13):
    chars = range(10) + list(string.uppercase)
    job_tag = ''.join(unicode(random.choice(chars)) for x in range(size))
    return 'i-{0}'.format(job_tag)

########NEW FILE########
__FILENAME__ = models
from moto.core import BaseBackend

from .utils import random_resource_id


class Role(object):

    def __init__(self, role_id, name, assume_role_policy_document, path, policies):
        self.id = role_id
        self.name = name
        self.assume_role_policy_document = assume_role_policy_document
        self.path = path
        self.policies = policies

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        return iam_backend.create_role(
            role_name=resource_name,
            assume_role_policy_document=properties['AssumeRolePolicyDocument'],
            path=properties['Path'],
            policies=properties.get('Policies', []),
        )

    @property
    def physical_resource_id(self):
        return self.id


class InstanceProfile(object):
    def __init__(self, instance_profile_id, name, path, roles):
        self.id = instance_profile_id
        self.name = name
        self.path = path
        self.roles = roles if roles else []

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        role_ids = properties['Roles']
        return iam_backend.create_instance_profile(
            name=resource_name,
            path=properties['Path'],
            role_ids=role_ids,
        )

    @property
    def physical_resource_id(self):
        return self.name


class IAMBackend(BaseBackend):

    def __init__(self):
        self.instance_profiles = {}
        self.roles = {}
        super(IAMBackend, self).__init__()

    def create_role(self, role_name, assume_role_policy_document, path, policies):
        role_id = random_resource_id()
        role = Role(role_id, role_name, assume_role_policy_document, path, policies)
        self.roles[role_id] = role
        return role

    def get_role_by_id(self, role_id):
        return self.roles.get(role_id)

    def get_role(self, role_name):
        for role in self.get_roles():
            if role.name == role_name:
                return role

    def get_roles(self):
        return self.roles.values()

    def create_instance_profile(self, name, path, role_ids):
        instance_profile_id = random_resource_id()

        roles = [iam_backend.get_role_by_id(role_id) for role_id in role_ids]
        instance_profile = InstanceProfile(instance_profile_id, name, path, roles)
        self.instance_profiles[instance_profile_id] = instance_profile
        return instance_profile

    def get_instance_profile(self, profile_name):
        for profile in self.get_instance_profiles():
            if profile.name == profile_name:
                return profile

    def get_instance_profiles(self):
        return self.instance_profiles.values()

    def add_role_to_instance_profile(self, profile_name, role_name):
        profile = self.get_instance_profile(profile_name)
        role = self.get_role(role_name)
        profile.roles.append(role)

iam_backend = IAMBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import iam_backend


class IamResponse(BaseResponse):

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def create_role(self):
        role_name = self._get_param('RoleName')
        path = self._get_param('Path')
        assume_role_policy_document = self._get_param('AssumeRolePolicyDocument')

        role = iam_backend.create_role(role_name, assume_role_policy_document, path, policies=[])
        template = Template(CREATE_ROLE_TEMPLATE)
        return template.render(role=role)

    def get_role(self):
        role_name = self._get_param('RoleName')
        role = iam_backend.get_role(role_name)

        template = Template(GET_ROLE_TEMPLATE)
        return template.render(role=role)

    def create_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        path = self._get_param('Path')

        profile = iam_backend.create_instance_profile(profile_name, path, role_ids=[])
        template = Template(CREATE_INSTANCE_PROFILE_TEMPLATE)
        return template.render(profile=profile)

    def get_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        profile = iam_backend.get_instance_profile(profile_name)

        template = Template(GET_INSTANCE_PROFILE_TEMPLATE)
        return template.render(profile=profile)

    def add_role_to_instance_profile(self):
        profile_name = self._get_param('InstanceProfileName')
        role_name = self._get_param('RoleName')

        iam_backend.add_role_to_instance_profile(profile_name, role_name)
        template = Template(ADD_ROLE_TO_INSTANCE_PROFILE_TEMPLATE)
        return template.render()

    def list_roles(self):
        roles = iam_backend.get_roles()

        template = Template(LIST_ROLES_TEMPLATE)
        return template.render(roles=roles)

    def list_instance_profiles(self):
        profiles = iam_backend.get_instance_profiles()

        template = Template(LIST_INSTANCE_PROFILES_TEMPLATE)
        return template.render(instance_profiles=profiles)

CREATE_INSTANCE_PROFILE_TEMPLATE = """<CreateInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <CreateInstanceProfileResult>
    <InstanceProfile>
      <InstanceProfileId>{{ profile.id }}</InstanceProfileId>
      <Roles/>
      <InstanceProfileName>{{ profile.name }}</InstanceProfileName>
      <Path>{{ profile.path }}</Path>
      <Arn>arn:aws:iam::123456789012:instance-profile/application_abc/component_xyz/Webserver</Arn>
      <CreateDate>2012-05-09T16:11:10.222Z</CreateDate>
    </InstanceProfile>
  </CreateInstanceProfileResult>
  <ResponseMetadata>
    <RequestId>974142ee-99f1-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</CreateInstanceProfileResponse>"""

GET_INSTANCE_PROFILE_TEMPLATE = """<GetInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <GetInstanceProfileResult>
    <InstanceProfile>
      <InstanceProfileId>{{ profile.id }}</InstanceProfileId>
      <Roles>
        {% for role in profile.roles %}
        <member>
          <Path>{{ role.path }}</Path>
          <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
          <RoleName>{{ role.name }}</RoleName>
          <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
          <CreateDate>2012-05-09T15:45:35Z</CreateDate>
          <RoleId>{{ role.id }}</RoleId>
        </member>
        {% endfor %}
      </Roles>
      <InstanceProfileName>{{ profile.name }}</InstanceProfileName>
      <Path>{{ profile.path }}</Path>
      <Arn>arn:aws:iam::123456789012:instance-profile/application_abc/component_xyz/Webserver</Arn>
      <CreateDate>2012-05-09T16:11:10Z</CreateDate>
    </InstanceProfile>
  </GetInstanceProfileResult>
  <ResponseMetadata>
    <RequestId>37289fda-99f2-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</GetInstanceProfileResponse>"""

CREATE_ROLE_TEMPLATE = """<CreateRoleResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <CreateRoleResult>
    <Role>
      <Path>{{ role.path }}</Path>
      <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
      <RoleName>{{ role.name }}</RoleName>
      <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
      <CreateDate>2012-05-08T23:34:01.495Z</CreateDate>
      <RoleId>{{ role.id }}</RoleId>
    </Role>
  </CreateRoleResult>
  <ResponseMetadata>
    <RequestId>4a93ceee-9966-11e1-b624-b1aEXAMPLE7c</RequestId>
  </ResponseMetadata>
</CreateRoleResponse>"""

GET_ROLE_TEMPLATE = """<GetRoleResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <GetRoleResult>
    <Role>
      <Path>{{ role.path }}</Path>
      <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
      <RoleName>{{ role.name }}</RoleName>
      <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
      <CreateDate>2012-05-08T23:34:01Z</CreateDate>
      <RoleId>{{ role.id }}</RoleId>
    </Role>
  </GetRoleResult>
  <ResponseMetadata>
    <RequestId>df37e965-9967-11e1-a4c3-270EXAMPLE04</RequestId>
  </ResponseMetadata>
</GetRoleResponse>"""

ADD_ROLE_TO_INSTANCE_PROFILE_TEMPLATE = """<AddRoleToInstanceProfileResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ResponseMetadata>
    <RequestId>12657608-99f2-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</AddRoleToInstanceProfileResponse>"""

LIST_ROLES_TEMPLATE = """<ListRolesResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ListRolesResult>
    <IsTruncated>false</IsTruncated>
    <Roles>
      {% for role in roles %}
      <member>
        <Path>{{ role.path }}</Path>
        <Arn>arn:aws:iam::123456789012:role/application_abc/component_xyz/S3Access</Arn>
        <RoleName>{{ role.name }}</RoleName>
        <AssumeRolePolicyDocument>{{ role.assume_role_policy_document }}</AssumeRolePolicyDocument>
        <CreateDate>2012-05-09T15:45:35Z</CreateDate>
        <RoleId>{{ role.id }}</RoleId>
      </member>
      {% endfor %}
    </Roles>
  </ListRolesResult>
  <ResponseMetadata>
    <RequestId>20f7279f-99ee-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</ListRolesResponse>"""

LIST_INSTANCE_PROFILES_TEMPLATE = """<ListInstanceProfilesResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ListInstanceProfilesResult>
    <IsTruncated>false</IsTruncated>
    <InstanceProfiles>
      {% for instance in instance_profiles %}
      <member>
        <Id>{{ instance.id }}</Id>
        <Roles/>
        <InstanceProfileName>{{ instance.name }}</InstanceProfileName>
        <Path>{{ instance.path }}</Path>
        <Arn>arn:aws:iam::123456789012:instance-profile/application_abc/component_xyz/Database</Arn>
        <CreateDate>2012-05-09T16:27:03Z</CreateDate>
      </member>
      {% endfor %}
    </InstanceProfiles>
  </ListInstanceProfilesResult>
  <ResponseMetadata>
    <RequestId>fd74fa8d-99f3-11e1-a4c3-27EXAMPLE804</RequestId>
  </ResponseMetadata>
</ListInstanceProfilesResponse>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import IamResponse

url_bases = [
    "https?://iam.amazonaws.com",
]

url_paths = {
    '{0}/$': IamResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import random
import string


def random_resource_id():
    size = 20
    chars = range(10) + list(string.lowercase)

    return ''.join(unicode(random.choice(chars)) for x in range(size))

########NEW FILE########
__FILENAME__ = models
from moto.core import BaseBackend
from moto.core.utils import get_random_hex


class FakeZone(object):

    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.rrsets = {}

    def add_rrset(self, name, rrset):
        self.rrsets[name] = rrset

    def delete_rrset(self, name):
        self.rrsets.pop(name, None)


class Route53Backend(BaseBackend):

    def __init__(self):
        self.zones = {}

    def create_hosted_zone(self, name):
        new_id = get_random_hex()
        new_zone = FakeZone(name, new_id)
        self.zones[new_id] = new_zone
        return new_zone

    def get_all_hosted_zones(self):
        return self.zones.values()

    def get_hosted_zone(self, id):
        return self.zones.get(id)

    def delete_hosted_zone(self, id):
        zone = self.zones.get(id)
        if zone:
            del self.zones[id]
            return zone
        return None


route53_backend = Route53Backend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template
from urlparse import parse_qs, urlparse
from .models import route53_backend
import xmltodict
import dicttoxml


def list_or_create_hostzone_response(request, full_url, headers):

    if request.method == "POST":
        elements = xmltodict.parse(request.body)
        new_zone = route53_backend.create_hosted_zone(elements["CreateHostedZoneRequest"]["Name"])
        template = Template(CREATE_HOSTED_ZONE_RESPONSE)
        return 201, headers, template.render(zone=new_zone)

    elif request.method == "GET":
        all_zones = route53_backend.get_all_hosted_zones()
        template = Template(LIST_HOSTED_ZONES_RESPONSE)
        return 200, headers, template.render(zones=all_zones)


def get_or_delete_hostzone_response(request, full_url, headers):
    parsed_url = urlparse(full_url)
    zoneid = parsed_url.path.rstrip('/').rsplit('/', 1)[1]
    the_zone = route53_backend.get_hosted_zone(zoneid)
    if not the_zone:
        return 404, headers, "Zone %s not Found" % zoneid

    if request.method == "GET":
        template = Template(GET_HOSTED_ZONE_RESPONSE)
        return 200, headers, template.render(zone=the_zone)
    elif request.method == "DELETE":
        route53_backend.delete_hosted_zone(zoneid)
        return 200, headers, DELETE_HOSTED_ZONE_RESPONSE


def rrset_response(request, full_url, headers):
    parsed_url = urlparse(full_url)
    method = request.method

    zoneid = parsed_url.path.rstrip('/').rsplit('/', 2)[1]
    the_zone = route53_backend.get_hosted_zone(zoneid)
    if not the_zone:
        return 404, headers, "Zone %s Not Found" % zoneid

    if method == "POST":
        elements = xmltodict.parse(request.body)

        change_list = elements['ChangeResourceRecordSetsRequest']['ChangeBatch']['Changes']['Change']
        if not isinstance(change_list, list):
            change_list = [elements['ChangeResourceRecordSetsRequest']['ChangeBatch']['Changes']['Change']]

        for value in change_list:
            action = value['Action']
            rrset = value['ResourceRecordSet']

            if action == 'CREATE':
                the_zone.add_rrset(rrset["Name"], rrset)
            elif action == "DELETE":
                the_zone.delete_rrset(rrset["Name"])

        return 200, headers, CHANGE_RRSET_RESPONSE

    elif method == "GET":
        querystring = parse_qs(parsed_url.query)
        template = Template(LIST_RRSET_REPONSE)
        rrset_list = []
        for key, value in the_zone.rrsets.items():
            if 'type' not in querystring or querystring["type"][0] == value["Type"]:
                rrset_list.append(dicttoxml.dicttoxml({"ResourceRecordSet": value}, root=False))

        return 200, headers, template.render(rrsets=rrset_list)


LIST_RRSET_REPONSE = """<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ResourceRecordSets>
   {% for rrset in rrsets %}
   {{ rrset }}
   {% endfor %}
   </ResourceRecordSets>
</ListResourceRecordSetsResponse>"""

CHANGE_RRSET_RESPONSE = """<ChangeResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ChangeInfo>
      <Status>PENDING</Status>
      <SubmittedAt>2010-09-10T01:36:41.958Z</SubmittedAt>
   </ChangeInfo>
</ChangeResourceRecordSetsResponse>"""

DELETE_HOSTED_ZONE_RESPONSE = """<DeleteHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <ChangeInfo>
   </ChangeInfo>
</DeleteHostedZoneResponse>"""

GET_HOSTED_ZONE_RESPONSE = """<GetHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <HostedZone>
      <Id>/hostedzone/{{ zone.id }}</Id>
      <Name>{{ zone.name }}</Name>
      <ResourceRecordSetCount>{{ zone.rrsets|count }}</ResourceRecordSetCount>
   </HostedZone>
   <DelegationSet>
         <NameServer>moto.test.com</NameServer>
   </DelegationSet>
</GetHostedZoneResponse>"""

CREATE_HOSTED_ZONE_RESPONSE = """<CreateHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/">
   <HostedZone>
      <Id>/hostedzone/{{ zone.id }}</Id>
      <Name>{{ zone.name }}</Name>
      <ResourceRecordSetCount>0</ResourceRecordSetCount>
   </HostedZone>
   <DelegationSet>
      <NameServers>
         <NameServer>moto.test.com</NameServer>
      </NameServers>
   </DelegationSet>
</CreateHostedZoneResponse>"""

LIST_HOSTED_ZONES_RESPONSE = """<ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2012-12-12/"> 
   <HostedZones>
      {% for zone in zones %}
      <HostedZone>
         <Id>{{ zone.id }}</Id>
         <Name>{{ zone.name }}</Name>
         <ResourceRecordSetCount>{{ zone.rrsets|count  }}</ResourceRecordSetCount>
      </HostedZone>
      {% endfor %}
   </HostedZones>
</ListHostedZonesResponse>"""

########NEW FILE########
__FILENAME__ = urls
import responses

url_bases = [
    "https://route53.amazonaws.com/201.-..-../hostedzone",
]

url_paths = {
    '{0}$': responses.list_or_create_hostzone_response,
    '{0}/.+$': responses.get_or_delete_hostzone_response,
    '{0}/.+/rrset$': responses.rrset_response,
}

########NEW FILE########
__FILENAME__ = exceptions
class BucketAlreadyExists(Exception):
    pass

########NEW FILE########
__FILENAME__ = models
import os
import base64
import datetime
import hashlib
import copy

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime, rfc_1123_datetime
from .exceptions import BucketAlreadyExists
from .utils import clean_key_name

UPLOAD_ID_BYTES = 43
UPLOAD_PART_MIN_SIZE = 5242880


class FakeKey(object):
    def __init__(self, name, value, storage="STANDARD", etag=None):
        self.name = name
        self.value = value
        self.last_modified = datetime.datetime.now()
        self._storage_class = storage
        self._metadata = {}
        self._expiry = None
        self._etag = etag

    def copy(self, new_name=None):
        r = copy.deepcopy(self)
        if new_name is not None:
            r.name = new_name
        return r

    def set_metadata(self, key, metadata):
        self._metadata[key] = metadata

    def clear_metadata(self):
        self._metadata = {}

    def set_storage_class(self, storage_class):
        self._storage_class = storage_class

    def append_to_value(self, value):
        self.value += value
        self.last_modified = datetime.datetime.now()
        self._etag = None  # must recalculate etag

    def restore(self, days):
        self._expiry = datetime.datetime.now() + datetime.timedelta(days)

    @property
    def etag(self):
        if self._etag is None:
            value_md5 = hashlib.md5()
            value_md5.update(bytes(self.value))
            self._etag = value_md5.hexdigest()
        return '"{0}"'.format(self._etag)

    @property
    def last_modified_ISO8601(self):
        return iso_8601_datetime(self.last_modified)

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return rfc_1123_datetime(self.last_modified)

    @property
    def metadata(self):
        return self._metadata

    @property
    def response_dict(self):
        r = {
            'etag': self.etag,
            'last-modified': self.last_modified_RFC1123,
        }
        if self._storage_class != 'STANDARD':
            r['x-amz-storage-class'] = self._storage_class
        if self._expiry is not None:
            rhdr = 'ongoing-request="false", expiry-date="{0}"'
            r['x-amz-restore'] = rhdr.format(self.expiry_date)
        return r

    @property
    def size(self):
        return len(self.value)

    @property
    def storage_class(self):
        return self._storage_class

    @property
    def expiry_date(self):
        if self._expiry is not None:
            return self._expiry.strftime("%a, %d %b %Y %H:%M:%S GMT")


class FakeMultipart(object):
    def __init__(self, key_name):
        self.key_name = key_name
        self.parts = {}
        self.id = base64.b64encode(os.urandom(UPLOAD_ID_BYTES)).replace('=', '').replace('+', '')

    def complete(self):
        total = bytearray()
        md5s = bytearray()
        last_part_name = len(self.list_parts())

        for part in self.list_parts():
            if part.name != last_part_name and len(part.value) < UPLOAD_PART_MIN_SIZE:
                return None, None
            md5s.extend(part.etag.replace('"', '').decode('hex'))
            total.extend(part.value)

        etag = hashlib.md5()
        etag.update(bytes(md5s))
        return total, "{0}-{1}".format(etag.hexdigest(), last_part_name)

    def set_part(self, part_id, value):
        if part_id < 1:
            return

        key = FakeKey(part_id, value)
        self.parts[part_id] = key
        return key

    def list_parts(self):
        parts = []

        for part_id, index in enumerate(sorted(self.parts.keys()), start=1):
            # Make sure part ids are continuous
            if part_id != index:
                return
            parts.append(self.parts[part_id])

        return parts


class FakeBucket(object):
    def __init__(self, name):
        self.name = name
        self.keys = {}
        self.multiparts = {}


class S3Backend(BaseBackend):

    def __init__(self):
        self.buckets = {}

    def create_bucket(self, bucket_name):
        if bucket_name in self.buckets:
            raise BucketAlreadyExists()
        new_bucket = FakeBucket(name=bucket_name)
        self.buckets[bucket_name] = new_bucket
        return new_bucket

    def get_all_buckets(self):
        return self.buckets.values()

    def get_bucket(self, bucket_name):
        return self.buckets.get(bucket_name)

    def delete_bucket(self, bucket_name):
        bucket = self.buckets.get(bucket_name)
        if bucket:
            if bucket.keys:
                # Can't delete a bucket with keys
                return False
            else:
                return self.buckets.pop(bucket_name)
        return None

    def set_key(self, bucket_name, key_name, value, storage=None, etag=None):
        key_name = clean_key_name(key_name)

        bucket = self.buckets[bucket_name]
        new_key = FakeKey(name=key_name, value=value,
                          storage=storage, etag=etag)
        bucket.keys[key_name] = new_key

        return new_key

    def append_to_key(self, bucket_name, key_name, value):
        key_name = clean_key_name(key_name)

        key = self.get_key(bucket_name, key_name)
        key.append_to_value(value)
        return key

    def get_key(self, bucket_name, key_name):
        key_name = clean_key_name(key_name)
        bucket = self.get_bucket(bucket_name)
        if bucket:
            return bucket.keys.get(key_name)

    def initiate_multipart(self, bucket_name, key_name):
        bucket = self.buckets[bucket_name]
        new_multipart = FakeMultipart(key_name)
        bucket.multiparts[new_multipart.id] = new_multipart

        return new_multipart

    def complete_multipart(self, bucket_name, multipart_id):
        bucket = self.buckets[bucket_name]
        multipart = bucket.multiparts[multipart_id]
        value, etag = multipart.complete()
        if value is None:
            return
        del bucket.multiparts[multipart_id]

        return self.set_key(bucket_name, multipart.key_name, value, etag=etag)

    def cancel_multipart(self, bucket_name, multipart_id):
        bucket = self.buckets[bucket_name]
        del bucket.multiparts[multipart_id]

    def list_multipart(self, bucket_name, multipart_id):
        bucket = self.buckets[bucket_name]
        return bucket.multiparts[multipart_id].list_parts()

    def get_all_multiparts(self, bucket_name):
        bucket = self.buckets[bucket_name]
        return bucket.multiparts

    def set_part(self, bucket_name, multipart_id, part_id, value):
        bucket = self.buckets[bucket_name]
        multipart = bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, value)

    def copy_part(self, dest_bucket_name, multipart_id, part_id,
                  src_bucket_name, src_key_name):
        src_key_name = clean_key_name(src_key_name)
        src_bucket = self.buckets[src_bucket_name]
        dest_bucket = self.buckets[dest_bucket_name]
        multipart = dest_bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, src_bucket.keys[src_key_name].value)

    def prefix_query(self, bucket, prefix, delimiter):
        key_results = set()
        folder_results = set()
        if prefix:
            for key_name, key in bucket.keys.iteritems():
                if key_name.startswith(prefix):
                    key_without_prefix = key_name.replace(prefix, "", 1)
                    if delimiter and delimiter in key_without_prefix:
                        # If delimiter, we need to split out folder_results
                        key_without_delimiter = key_without_prefix.split(delimiter)[0]
                        folder_results.add("{0}{1}{2}".format(prefix, key_without_delimiter, delimiter))
                    else:
                        key_results.add(key)
        else:
            for key_name, key in bucket.keys.iteritems():
                if delimiter and delimiter in key_name:
                    # If delimiter, we need to split out folder_results
                    folder_results.add(key_name.split(delimiter)[0])
                else:
                    key_results.add(key)

        key_results = sorted(key_results, key=lambda key: key.name)
        folder_results = [folder_name for folder_name in sorted(folder_results, key=lambda key: key)]

        return key_results, folder_results

    def delete_key(self, bucket_name, key_name):
        key_name = clean_key_name(key_name)
        bucket = self.buckets[bucket_name]
        return bucket.keys.pop(key_name)

    def copy_key(self, src_bucket_name, src_key_name, dest_bucket_name, dest_key_name, storage=None):
        src_key_name = clean_key_name(src_key_name)
        dest_key_name = clean_key_name(dest_key_name)
        src_bucket = self.buckets[src_bucket_name]
        dest_bucket = self.buckets[dest_bucket_name]
        key = src_bucket.keys[src_key_name]
        if dest_key_name != src_key_name:
            key = key.copy(dest_key_name)
        dest_bucket.keys[dest_key_name] = key
        if storage is not None:
            dest_bucket.keys[dest_key_name].set_storage_class(storage)

s3_backend = S3Backend()

########NEW FILE########
__FILENAME__ = responses
from urlparse import parse_qs, urlparse
import re

from jinja2 import Template

from .exceptions import BucketAlreadyExists
from .models import s3_backend
from .utils import bucket_name_from_url
from xml.dom import minidom


def parse_key_name(pth):
    return pth.lstrip("/")


class ResponseObject(object):
    def __init__(self, backend, bucket_name_from_url, parse_key_name):
        self.backend = backend
        self.bucket_name_from_url = bucket_name_from_url
        self.parse_key_name = parse_key_name

    def all_buckets(self):
        # No bucket specified. Listing all buckets
        all_buckets = self.backend.get_all_buckets()
        template = Template(S3_ALL_BUCKETS)
        return template.render(buckets=all_buckets)

    def bucket_response(self, request, full_url, headers):
        response = self._bucket_response(request, full_url, headers)
        if isinstance(response, basestring):
            return 200, headers, response
        else:
            status_code, headers, response_content = response
            return status_code, headers, response_content

    def _bucket_response(self, request, full_url, headers):
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        method = request.method

        bucket_name = self.bucket_name_from_url(full_url)
        if not bucket_name:
            # If no bucket specified, list all buckets
            return self.all_buckets()

        if method == 'HEAD':
            return self._bucket_response_head(bucket_name, headers)
        elif method == 'GET':
            return self._bucket_response_get(bucket_name, querystring, headers)
        elif method == 'PUT':
            return self._bucket_response_put(bucket_name, headers)
        elif method == 'DELETE':
            return self._bucket_response_delete(bucket_name, headers)
        elif method == 'POST':
            return self._bucket_response_post(request, bucket_name, headers)
        else:
            raise NotImplementedError("Method {0} has not been impelemented in the S3 backend yet".format(method))

    def _bucket_response_head(self, bucket_name, headers):
        bucket = self.backend.get_bucket(bucket_name)
        if bucket:
            return 200, headers, ""
        else:
            return 404, headers, ""

    def _bucket_response_get(self, bucket_name, querystring, headers):
        if 'uploads' in querystring:
            for unsup in ('delimiter', 'prefix', 'max-uploads'):
                if unsup in querystring:
                    raise NotImplementedError("Listing multipart uploads with {} has not been implemented yet.".format(unsup))
            multiparts = list(self.backend.get_all_multiparts(bucket_name).itervalues())
            template = Template(S3_ALL_MULTIPARTS)
            return 200, headers, template.render(
                bucket_name=bucket_name,
                uploads=multiparts)

        bucket = self.backend.get_bucket(bucket_name)
        if bucket:
            prefix = querystring.get('prefix', [None])[0]
            delimiter = querystring.get('delimiter', [None])[0]
            result_keys, result_folders = self.backend.prefix_query(bucket, prefix, delimiter)
            template = Template(S3_BUCKET_GET_RESPONSE)
            return template.render(
                bucket=bucket,
                prefix=prefix,
                delimiter=delimiter,
                result_keys=result_keys,
                result_folders=result_folders
            )
        else:
            return 404, headers, ""

    def _bucket_response_put(self, bucket_name, headers):
        try:
            new_bucket = self.backend.create_bucket(bucket_name)
        except BucketAlreadyExists:
            return 409, headers, ""
        template = Template(S3_BUCKET_CREATE_RESPONSE)
        return template.render(bucket=new_bucket)

    def _bucket_response_delete(self, bucket_name, headers):
        removed_bucket = self.backend.delete_bucket(bucket_name)
        if removed_bucket is None:
            # Non-existant bucket
            template = Template(S3_DELETE_NON_EXISTING_BUCKET)
            return 404, headers, template.render(bucket_name=bucket_name)
        elif removed_bucket:
            # Bucket exists
            template = Template(S3_DELETE_BUCKET_SUCCESS)
            return 204, headers, template.render(bucket=removed_bucket)
        else:
            # Tried to delete a bucket that still has keys
            template = Template(S3_DELETE_BUCKET_WITH_ITEMS_ERROR)
            return 409, headers, template.render(bucket=removed_bucket)

    def _bucket_response_post(self, request, bucket_name, headers):
        if request.path == u'/?delete':
            return self._bucket_response_delete_keys(request, bucket_name, headers)

        #POST to bucket-url should create file from form
        if hasattr(request, 'form'):
            #Not HTTPretty
            form = request.form
        else:
            #HTTPretty, build new form object
            form = {}
            for kv in request.body.split('&'):
                k, v = kv.split('=')
                form[k] = v

        key = form['key']
        if 'file' in form:
            f = form['file']
        else:
            f = request.files['file'].stream.read()

        new_key = self.backend.set_key(bucket_name, key, f)

        #Metadata
        meta_regex = re.compile('^x-amz-meta-([a-zA-Z0-9\-_]+)$', flags=re.IGNORECASE)

        for form_id in form:
            result = meta_regex.match(form_id)
            if result:
                meta_key = result.group(0).lower()
                metadata = form[form_id]
                new_key.set_metadata(meta_key, metadata)
        return 200, headers, ""

    def _bucket_response_delete_keys(self, request, bucket_name, headers):
        template = Template(S3_DELETE_KEYS_RESPONSE)

        keys = minidom.parseString(request.body).getElementsByTagName('Key')
        deleted_names = []
        error_names = []

        for k in keys:
            try:
                key_name = k.firstChild.nodeValue
                self.backend.delete_key(bucket_name, key_name)
                deleted_names.append(key_name)
            except KeyError as e:
                error_names.append(key_name)

        return 200, headers, template.render(deleted=deleted_names,delete_errors=error_names)

    def key_response(self, request, full_url, headers):
        response = self._key_response(request, full_url, headers)
        if isinstance(response, basestring):
            return 200, headers, response
        else:
            status_code, headers, response_content = response
            return status_code, headers, response_content

    def _key_set_metadata(self, request, key, replace=False):
        meta_regex = re.compile('^x-amz-meta-([a-zA-Z0-9\-_]+)$', flags=re.IGNORECASE)
        if replace is True:
            key.clear_metadata()
        for header in request.headers:
            if isinstance(header, basestring):
                result = meta_regex.match(header)
                if result:
                    meta_key = result.group(0).lower()
                    metadata = request.headers[header]
                    key.set_metadata(meta_key, metadata)

    def _key_response(self, request, full_url, headers):
        parsed_url = urlparse(full_url)
        query = parse_qs(parsed_url.query)
        method = request.method

        key_name = self.parse_key_name(parsed_url.path)
        bucket_name = self.bucket_name_from_url(full_url)

        if hasattr(request, 'body'):
            # Boto
            body = request.body
        else:
            # Flask server
            body = request.data

        if method == 'GET':
            return self._key_response_get(bucket_name, query, key_name, headers)
        elif method == 'PUT':
            return self._key_response_put(request, body, bucket_name, query, key_name, headers)
        elif method == 'HEAD':
            return self._key_response_head(bucket_name, key_name, headers)
        elif method == 'DELETE':
            return self._key_response_delete(bucket_name, query, key_name, headers)
        elif method == 'POST':
            return self._key_response_post(body, parsed_url, bucket_name, query, key_name, headers)
        else:
            raise NotImplementedError("Method {0} has not been impelemented in the S3 backend yet".format(method))

    def _key_response_get(self, bucket_name, query, key_name, headers):
        if 'uploadId' in query:
            upload_id = query['uploadId'][0]
            parts = self.backend.list_multipart(bucket_name, upload_id)
            template = Template(S3_MULTIPART_LIST_RESPONSE)
            return 200, headers, template.render(
                bucket_name=bucket_name,
                key_name=key_name,
                upload_id=upload_id,
                count=len(parts),
                parts=parts
            )
        key = self.backend.get_key(bucket_name, key_name)
        if key:
            headers.update(key.metadata)
            return 200, headers, key.value
        else:
            return 404, headers, ""

    def _key_response_put(self, request, body, bucket_name, query, key_name, headers):
        if 'uploadId' in query and 'partNumber' in query:
            upload_id = query['uploadId'][0]
            part_number = int(query['partNumber'][0])
            if 'x-amz-copy-source' in request.headers:
                src = request.headers.get("x-amz-copy-source")
                src_bucket, src_key = src.split("/", 1)
                key = self.backend.copy_part(
                    bucket_name, upload_id, part_number, src_bucket,
                    src_key)
                template = Template(S3_MULTIPART_UPLOAD_RESPONSE)
                response = template.render(part=key)
            else:
                key = self.backend.set_part(
                    bucket_name, upload_id, part_number, body)
                response = ""
            headers.update(key.response_dict)
            return 200, headers, response

        storage_class = request.headers.get('x-amz-storage-class', 'STANDARD')

        if 'x-amz-copy-source' in request.headers:
            # Copy key
            src_bucket, src_key = request.headers.get("x-amz-copy-source").split("/", 1)
            self.backend.copy_key(src_bucket, src_key, bucket_name, key_name,
                                  storage=storage_class)
            mdirective = request.headers.get('x-amz-metadata-directive')
            if mdirective is not None and mdirective == 'REPLACE':
                new_key = self.backend.get_key(bucket_name, key_name)
                self._key_set_metadata(request, new_key, replace=True)
            template = Template(S3_OBJECT_COPY_RESPONSE)
            return template.render(key=src_key)
        streaming_request = hasattr(request, 'streaming') and request.streaming
        closing_connection = headers.get('connection') == 'close'
        if closing_connection and streaming_request:
            # Closing the connection of a streaming request. No more data
            new_key = self.backend.get_key(bucket_name, key_name)
        elif streaming_request:
            # Streaming request, more data
            new_key = self.backend.append_to_key(bucket_name, key_name, body)
        else:
            # Initial data
            new_key = self.backend.set_key(bucket_name, key_name, body,
                                           storage=storage_class)
            request.streaming = True
            self._key_set_metadata(request, new_key)

        template = Template(S3_OBJECT_RESPONSE)
        headers.update(new_key.response_dict)
        return 200, headers, template.render(key=new_key)

    def _key_response_head(self, bucket_name, key_name, headers):
        key = self.backend.get_key(bucket_name, key_name)
        if key:
            headers.update(key.metadata)
            headers.update(key.response_dict)
            return 200, headers, ""
        else:
            return 404, headers, ""

    def _key_response_delete(self, bucket_name, query, key_name, headers):
        if 'uploadId' in query:
            upload_id = query['uploadId'][0]
            self.backend.cancel_multipart(bucket_name, upload_id)
            return 204, headers, ""
        removed_key = self.backend.delete_key(bucket_name, key_name)
        template = Template(S3_DELETE_OBJECT_SUCCESS)
        return 204, headers, template.render(bucket=removed_key)

    def _key_response_post(self, body, parsed_url, bucket_name, query, key_name, headers):
        if body == '' and parsed_url.query == 'uploads':
            multipart = self.backend.initiate_multipart(bucket_name, key_name)
            template = Template(S3_MULTIPART_INITIATE_RESPONSE)
            response = template.render(
                bucket_name=bucket_name,
                key_name=key_name,
                upload_id=multipart.id,
            )
            return 200, headers, response

        if 'uploadId' in query:
            upload_id = query['uploadId'][0]
            key = self.backend.complete_multipart(bucket_name, upload_id)

            if key is not None:
                template = Template(S3_MULTIPART_COMPLETE_RESPONSE)
                return template.render(
                    bucket_name=bucket_name,
                    key_name=key.name,
                    etag=key.etag,
                )
            template = Template(S3_MULTIPART_COMPLETE_TOO_SMALL_ERROR)
            return 400, headers, template.render()
        elif parsed_url.query == 'restore':
            es = minidom.parseString(body).getElementsByTagName('Days')
            days = es[0].childNodes[0].wholeText
            key = self.backend.get_key(bucket_name, key_name)
            r = 202
            if key.expiry_date is not None:
                r = 200
            key.restore(int(days))
            return r, headers, ""
        else:
            raise NotImplementedError("Method POST had only been implemented for multipart uploads and restore operations, so far")

S3ResponseInstance = ResponseObject(s3_backend, bucket_name_from_url, parse_key_name)

S3_ALL_BUCKETS = """<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <Owner>
    <ID>bcaf1ffd86f41161ca5fb16fd081034f</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <Buckets>
    {% for bucket in buckets %}
      <Bucket>
        <Name>{{ bucket.name }}</Name>
        <CreationDate>2006-02-03T16:45:09.000Z</CreationDate>
      </Bucket>
    {% endfor %}
 </Buckets>
</ListAllMyBucketsResult>"""

S3_BUCKET_GET_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>{{ bucket.name }}</Name>
  <Prefix>{{ prefix }}</Prefix>
  <MaxKeys>1000</MaxKeys>
  <Delimiter>{{ delimiter }}</Delimiter>
  <IsTruncated>false</IsTruncated>
  {% for key in result_keys %}
    <Contents>
      <Key>{{ key.name }}</Key>
      <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
      <ETag>{{ key.etag }}</ETag>
      <Size>{{ key.size }}</Size>
      <StorageClass>{{ key.storage_class }}</StorageClass>
      <Owner>
        <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
        <DisplayName>webfile</DisplayName>
      </Owner>
    </Contents>
  {% endfor %}
  {% if delimiter %}
    {% for folder in result_folders %}
      <CommonPrefixes>
        <Prefix>{{ folder }}</Prefix>
      </CommonPrefixes>
    {% endfor %}
  {% endif %}
  </ListBucketResult>"""

S3_BUCKET_CREATE_RESPONSE = """<CreateBucketResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <CreateBucketResponse>
    <Bucket>{{ bucket.name }}</Bucket>
  </CreateBucketResponse>
</CreateBucketResponse>"""

S3_DELETE_BUCKET_SUCCESS = """<DeleteBucketResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <DeleteBucketResponse>
    <Code>204</Code>
    <Description>No Content</Description>
  </DeleteBucketResponse>
</DeleteBucketResponse>"""

S3_DELETE_NON_EXISTING_BUCKET = """<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>NoSuchBucket</Code>
<Message>The specified bucket does not exist</Message>
<BucketName>{{ bucket_name }}</BucketName>
<RequestId>asdfasdfsadf</RequestId>
<HostId>asfasdfsfsafasdf</HostId>
</Error>"""

S3_DELETE_BUCKET_WITH_ITEMS_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>BucketNotEmpty</Code>
<Message>The bucket you tried to delete is not empty</Message>
<BucketName>{{ bucket.name }}</BucketName>
<RequestId>asdfasdfsdafds</RequestId>
<HostId>sdfgdsfgdsfgdfsdsfgdfs</HostId>
</Error>"""

S3_DELETE_KEYS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<DeleteResult xmlns="http://s3.amazonaws.com/doc/2006-03-01">
{% for k in deleted %}
<Deleted>
<Key>{{k}}</Key>
</Deleted>
{% endfor %}
{% for k in delete_errors %}
<Error>
<Key>{{k}}</Key>
</Error>
{% endfor %}
</DeleteResult>"""

S3_DELETE_OBJECT_SUCCESS = """<DeleteObjectResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <DeleteObjectResponse>
    <Code>200</Code>
    <Description>OK</Description>
  </DeleteObjectResponse>
</DeleteObjectResponse>"""

S3_OBJECT_RESPONSE = """<PutObjectResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
      <PutObjectResponse>
        <ETag>{{ key.etag }}</ETag>
        <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
      </PutObjectResponse>
    </PutObjectResponse>"""

S3_OBJECT_COPY_RESPONSE = """<CopyObjectResponse xmlns="http://doc.s3.amazonaws.com/2006-03-01">
  <CopyObjectResponse>
    <ETag>{{ key.etag }}</ETag>
    <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
  </CopyObjectResponse>
</CopyObjectResponse>"""

S3_MULTIPART_INITIATE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<InitiateMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <UploadId>{{ upload_id }}</UploadId>
</InitiateMultipartUploadResult>"""

S3_MULTIPART_UPLOAD_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CopyPartResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <LastModified>{{ part.last_modified_ISO8601 }}</LastModified>
  <ETag>{{ part.etag }}</ETag>
</CopyPartResult>"""

S3_MULTIPART_LIST_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListPartsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <UploadId>{{ upload_id }}</UploadId>
  <StorageClass>STANDARD</StorageClass>
  <Initiator>
    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
    <DisplayName>webfile</DisplayName>
  </Initiator>
  <Owner>
    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <StorageClass>STANDARD</StorageClass>
  <PartNumberMarker>1</PartNumberMarker>
  <NextPartNumberMarker>{{ count }} </NextPartNumberMarker>
  <MaxParts>{{ count }}</MaxParts>
  <IsTruncated>false</IsTruncated>
  {% for part in parts %}
  <Part>
    <PartNumber>{{ part.name }}</PartNumber>
    <LastModified>{{ part.last_modified_ISO8601 }}</LastModified>
    <ETag>{{ part.etag }}</ETag>
    <Size>{{ part.size }}</Size>
  </Part>
  {% endfor %}
</ListPartsResult>"""

S3_MULTIPART_COMPLETE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CompleteMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Location>http://{{ bucket_name }}.s3.amazonaws.com/{{ key_name }}</Location>
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <ETag>{{ etag }}</ETag>
</CompleteMultipartUploadResult>
"""

S3_MULTIPART_COMPLETE_TOO_SMALL_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>EntityTooSmall</Code>
  <Message>Your proposed upload is smaller than the minimum allowed object size.</Message>
  <RequestId>asdfasdfsdafds</RequestId>
  <HostId>sdfgdsfgdsfgdfsdsfgdfs</HostId>
</Error>"""

S3_ALL_MULTIPARTS = """<?xml version="1.0" encoding="UTF-8"?>
<ListMultipartUploadsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <KeyMarker></KeyMarker>
  <UploadIdMarker></UploadIdMarker>
  <MaxUploads>1000</MaxUploads>
  <IsTruncated>False</IsTruncated>
  {% for upload in uploads %}
  <Upload>
    <Key>{{ upload.key_name }}</Key>
    <UploadId>{{ upload.id }}</UploadId>
    <Initiator>
      <ID>arn:aws:iam::111122223333:user/user1-11111a31-17b5-4fb7-9df5-b111111f13de</ID>
      <DisplayName>user1-11111a31-17b5-4fb7-9df5-b111111f13de</DisplayName>
    </Initiator>
    <Owner>
      <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
      <DisplayName>OwnerDisplayName</DisplayName>
    </Owner>
    <StorageClass>STANDARD</StorageClass>
    <Initiated>2010-11-10T20:48:33.000Z</Initiated>
  </Upload>
  {% endfor %}
</ListMultipartUploadsResult>
"""

########NEW FILE########
__FILENAME__ = urls
from .responses import S3ResponseInstance

url_bases = [
    "https?://(?P<bucket_name>[a-zA-Z0-9\-_.]*)\.?s3.amazonaws.com"
]

url_paths = {
    '{0}/$': S3ResponseInstance.bucket_response,
    '{0}/(?P<key_name>.+)': S3ResponseInstance.key_response,
}

########NEW FILE########
__FILENAME__ = utils
import re
import urllib2
import urlparse

bucket_name_regex = re.compile("(.+).s3.amazonaws.com")


def bucket_name_from_url(url):
    domain = urlparse.urlparse(url).netloc

    if domain.startswith('www.'):
        domain = domain[4:]

    if 'amazonaws.com' in domain:
        bucket_result = bucket_name_regex.search(domain)
        if bucket_result:
            return bucket_result.groups()[0]
    else:
        if '.' in domain:
            return domain.split(".")[0]
        else:
            # No subdomain found.
            return None


def clean_key_name(key_name):
    return urllib2.unquote(key_name)

########NEW FILE########
__FILENAME__ = models
from moto.s3.models import S3Backend


class S3BucketPathBackend(S3Backend):
    pass

s3bucket_path_backend = S3BucketPathBackend()

########NEW FILE########
__FILENAME__ = responses
from .models import s3bucket_path_backend

from .utils import bucket_name_from_url

from moto.s3.responses import ResponseObject


def parse_key_name(pth):
    return "/".join(pth.rstrip("/").split("/")[2:])

S3BucketPathResponseInstance = ResponseObject(
    s3bucket_path_backend,
    bucket_name_from_url,
    parse_key_name,
)

########NEW FILE########
__FILENAME__ = urls
from .responses import S3BucketPathResponseInstance as ro

url_bases = [
    "https?://s3.amazonaws.com"
]


def bucket_response2(*args):
    return ro.bucket_response(*args)


def bucket_response3(*args):
    return ro.bucket_response(*args)

url_paths = {
    '{0}/$': bucket_response3,
    '{0}/(?P<bucket_name>[a-zA-Z0-9\-_.]+)$': ro.bucket_response,
    '{0}/(?P<bucket_name>[a-zA-Z0-9\-_.]+)/$': bucket_response2,
    '{0}/(?P<bucket_name>[a-zA-Z0-9\-_./]+)/(?P<key_name>.+)': ro.key_response
}

########NEW FILE########
__FILENAME__ = utils
import urlparse


def bucket_name_from_url(url):
    pth = urlparse.urlparse(url).path.lstrip("/")

    l = pth.lstrip("/").split("/")
    if len(l) == 0 or l[0] == "":
        return None
    return l[0]

########NEW FILE########
__FILENAME__ = server
import re
import sys
import argparse

from threading import Lock

from flask import Flask
from werkzeug.routing import BaseConverter
from werkzeug.serving import run_simple

from moto.backends import BACKENDS
from moto.core.utils import convert_flask_to_httpretty_response

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]


class DomainDispatcherApplication(object):
    """
    Dispatch requests to different applications based on the "Host:" header
    value. We'll match the host header value with the url_bases of each backend.
    """

    def __init__(self, create_app, service=None):
        self.create_app = create_app
        self.lock = Lock()
        self.app_instances = {}
        self.service = service

    def get_backend_for_host(self, host):
        if self.service:
            return self.service

        for backend_name, backend in BACKENDS.iteritems():
            for url_base in backend.url_bases:
                if re.match(url_base, 'http://%s' % host):
                    return backend_name

        raise RuntimeError('Invalid host: "%s"' % host)

    def get_application(self, host):
        host = host.split(':')[0]
        with self.lock:
            backend = self.get_backend_for_host(host)
            app = self.app_instances.get(backend, None)
            if app is None:
                app = self.create_app(backend)
                self.app_instances[backend] = app
            return app

    def __call__(self, environ, start_response):
        backend_app = self.get_application(environ['HTTP_HOST'])
        return backend_app(environ, start_response)


class RegexConverter(BaseConverter):
    # http://werkzeug.pocoo.org/docs/routing/#custom-converters
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def create_backend_app(service):
    from werkzeug.routing import Map

    # Create the backend_app
    backend_app = Flask(__name__)
    backend_app.debug = True

    # Reset view functions to reset the app
    backend_app.view_functions = {}
    backend_app.url_map = Map()
    backend_app.url_map.converters['regex'] = RegexConverter

    backend = BACKENDS[service]
    for url_path, handler in backend.flask_paths.iteritems():
        backend_app.route(url_path, methods=HTTP_METHODS)(convert_flask_to_httpretty_response(handler))

    return backend_app


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()

    # Keep this for backwards compat
    parser.add_argument(
        "service",
        type=str,
        nargs='?',  # http://stackoverflow.com/a/4480202/731592
        default=None)
    parser.add_argument(
        '-H', '--host', type=str,
        help='Which host to bind',
        default='0.0.0.0')
    parser.add_argument(
        '-p', '--port', type=int,
        help='Port number to use for connection',
        default=5000)

    args = parser.parse_args(argv)

    # Wrap the main application
    main_app = DomainDispatcherApplication(create_backend_app, service=args.service)
    main_app.debug = True

    run_simple(args.host, args.port, main_app)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models
from moto.core import BaseBackend
from .utils import get_random_message_id


class Message(object):
    def __init__(self, message_id, source, subject, body, destination):
        self.id = message_id
        self.source = source
        self.subject = subject
        self.body = body
        self.destination = destination


class RawMessage(object):
    def __init__(self, message_id, source, destination, raw_data):
        self.id = message_id
        self.source = source
        self.destination = destination
        self.raw_data = raw_data


class SESQuota(object):
    def __init__(self, messages):
        self.messages = messages

    @property
    def sent_past_24(self):
        return len(self.messages)


class SESBackend(BaseBackend):
    def __init__(self):
        self.addresses = []
        self.sent_messages = []

    def verify_email_identity(self, address):
        self.addresses.append(address)

    def verify_domain(self, domain):
        self.addresses.append(domain)

    def list_identities(self):
        return self.addresses

    def delete_identity(self, identity):
        self.addresses.remove(identity)

    def send_email(self, source, subject, body, destination):
        if source not in self.addresses:
            return False

        message_id = get_random_message_id()
        message = Message(message_id, source, subject, body, destination)
        self.sent_messages.append(message)
        return message

    def send_raw_email(self, source, destination, raw_data):
        if source not in self.addresses:
            return False

        message_id = get_random_message_id()
        message = RawMessage(message_id, source, destination, raw_data)
        self.sent_messages.append(message)
        return message

    def get_send_quota(self):
        return SESQuota(self.sent_messages)

ses_backend = SESBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import ses_backend


class EmailResponse(BaseResponse):

    def verify_email_identity(self):
        address = self.querystring.get('EmailAddress')[0]
        ses_backend.verify_email_identity(address)
        template = Template(VERIFY_EMAIL_IDENTITY)
        return template.render()

    def list_identities(self):
        identities = ses_backend.list_identities()
        template = Template(LIST_IDENTITIES_RESPONSE)
        return template.render(identities=identities)

    def verify_domain_dkim(self):
        domain = self.querystring.get('Domain')[0]
        ses_backend.verify_domain(domain)
        template = Template(VERIFY_DOMAIN_DKIM_RESPONSE)
        return template.render()

    def verify_domain_identity(self):
        domain = self.querystring.get('Domain')[0]
        ses_backend.verify_domain(domain)
        template = Template(VERIFY_DOMAIN_DKIM_RESPONSE)
        return template.render()

    def delete_identity(self):
        domain = self.querystring.get('Identity')[0]
        ses_backend.delete_identity(domain)
        template = Template(DELETE_IDENTITY_RESPONSE)
        return template.render()

    def send_email(self):
        bodydatakey = 'Message.Body.Text.Data'
        if 'Message.Body.Html.Data' in self.querystring:
            bodydatakey = 'Message.Body.Html.Data'
        body = self.querystring.get(bodydatakey)[0]
        source = self.querystring.get('Source')[0]
        subject = self.querystring.get('Message.Subject.Data')[0]
        destination = self.querystring.get('Destination.ToAddresses.member.1')[0]
        message = ses_backend.send_email(source, subject, body, destination)
        if not message:
            return "Did not have authority to send from email {0}".format(source), dict(status=400)
        template = Template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)

    def send_raw_email(self):
        source = self.querystring.get('Source')[0]
        destination = self.querystring.get('Destinations.member.1')[0]
        raw_data = self.querystring.get('RawMessage.Data')[0]

        message = ses_backend.send_raw_email(source, destination, raw_data)
        if not message:
            return "Did not have authority to send from email {0}".format(source), dict(status=400)
        template = Template(SEND_RAW_EMAIL_RESPONSE)
        return template.render(message=message)

    def get_send_quota(self):
        quota = ses_backend.get_send_quota()
        template = Template(GET_SEND_QUOTA_RESPONSE)
        return template.render(quota=quota)


VERIFY_EMAIL_IDENTITY = """<VerifyEmailIdentityResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyEmailIdentityResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</VerifyEmailIdentityResponse>"""

LIST_IDENTITIES_RESPONSE = """<ListIdentitiesResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <ListIdentitiesResult>
    <Identities>
        {% for identity in identities %}
          <member>{{ identity }}</member>
        {% endfor %}
    </Identities>
  </ListIdentitiesResult>
  <ResponseMetadata>
    <RequestId>cacecf23-9bf1-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</ListIdentitiesResponse>"""

VERIFY_DOMAIN_DKIM_RESPONSE = """<VerifyDomainDkimResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyDomainDkimResult>
    <DkimTokens>
      <member>vvjuipp74whm76gqoni7qmwwn4w4qusjiainivf6sf</member>
      <member>3frqe7jn4obpuxjpwpolz6ipb3k5nvt2nhjpik2oy</member>
      <member>wrqplteh7oodxnad7hsl4mixg2uavzneazxv5sxi2</member>
    </DkimTokens>
    </VerifyDomainDkimResult>
    <ResponseMetadata>
      <RequestId>9662c15b-c469-11e1-99d1-797d6ecd6414</RequestId>
    </ResponseMetadata>
</VerifyDomainDkimResponse>"""

DELETE_IDENTITY_RESPONSE = """<DeleteIdentityResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <DeleteIdentityResult/>
  <ResponseMetadata>
    <RequestId>d96bd874-9bf2-11e1-8ee7-c98a0037a2b6</RequestId>
  </ResponseMetadata>
</DeleteIdentityResponse>"""

SEND_EMAIL_RESPONSE = """<SendEmailResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SendEmailResult>
    <MessageId>{{ message.id }}</MessageId>
  </SendEmailResult>
  <ResponseMetadata>
    <RequestId>d5964849-c866-11e0-9beb-01a62d68c57f</RequestId>
  </ResponseMetadata>
</SendEmailResponse>"""

SEND_RAW_EMAIL_RESPONSE = """<SendRawEmailResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SendRawEmailResult>
    <MessageId>{{ message.id }}</MessageId>
  </SendRawEmailResult>
  <ResponseMetadata>
    <RequestId>e0abcdfa-c866-11e0-b6d0-273d09173b49</RequestId>
  </ResponseMetadata>
</SendRawEmailResponse>"""

GET_SEND_QUOTA_RESPONSE = """<GetSendQuotaResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <GetSendQuotaResult>
    <SentLast24Hours>{{ quota.sent_past_24 }}</SentLast24Hours>
    <Max24HourSend>200.0</Max24HourSend>
    <MaxSendRate>1.0</MaxSendRate>
  </GetSendQuotaResult>
  <ResponseMetadata>
    <RequestId>273021c6-c866-11e0-b926-699e21c3af9e</RequestId>
  </ResponseMetadata>
</GetSendQuotaResponse>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import EmailResponse

url_bases = [
    "https?://email.(.+).amazonaws.com"
]

url_paths = {
    '{0}/$': EmailResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import random
import string


def random_hex(length):
    return ''.join(random.choice(string.lowercase) for x in range(length))


def get_random_message_id():
    return "{0}-{1}-{2}-{3}-{4}-{5}-{6}".format(
           random_hex(16),
           random_hex(8),
           random_hex(4),
           random_hex(4),
           random_hex(4),
           random_hex(12),
           random_hex(6),
    )

########NEW FILE########
__FILENAME__ = models
import datetime
import requests
import uuid

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime
from moto.sqs.models import sqs_backend
from .utils import make_arn_for_topic, make_arn_for_subscription

DEFAULT_ACCOUNT_ID = 123456789012


class Topic(object):
    def __init__(self, name):
        self.name = name
        self.account_id = DEFAULT_ACCOUNT_ID
        self.display_name = ""
        self.policy = DEFAULT_TOPIC_POLICY
        self.delivery_policy = ""
        self.effective_delivery_policy = DEFAULT_EFFECTIVE_DELIVERY_POLICY
        self.arn = make_arn_for_topic(self.account_id, name)

        self.subscriptions_pending = 0
        self.subscriptions_confimed = 0
        self.subscriptions_deleted = 0

    def publish(self, message):
        message_id = unicode(uuid.uuid4())
        subscriptions = sns_backend.list_subscriptions(self.arn)
        for subscription in subscriptions:
            subscription.publish(message, message_id)
        return message_id


class Subscription(object):
    def __init__(self, topic, endpoint, protocol):
        self.topic = topic
        self.endpoint = endpoint
        self.protocol = protocol
        self.arn = make_arn_for_subscription(self.topic.arn)

    def publish(self, message, message_id):
        if self.protocol == 'sqs':
            queue_name = self.endpoint.split(":")[-1]
            sqs_backend.send_message(queue_name, message)
        elif self.protocol in ['http', 'https']:
            post_data = self.get_post_data(message, message_id)
            requests.post(self.endpoint, data=post_data)

    def get_post_data(self, message, message_id):
        return {
            "Type": "Notification",
            "MessageId": message_id,
            "TopicArn": self.topic.arn,
            "Subject": "my subject",
            "Message": message,
            "Timestamp": iso_8601_datetime(datetime.datetime.now()),
            "SignatureVersion": "1",
            "Signature": "EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc=",
            "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem",
            "UnsubscribeURL": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"
        }


class SNSBackend(BaseBackend):
    def __init__(self):
        self.topics = {}
        self.subscriptions = {}

    def create_topic(self, name):
        topic = Topic(name)
        self.topics[topic.arn] = topic
        return topic

    def list_topics(self):
        return self.topics.values()

    def delete_topic(self, arn):
        self.topics.pop(arn)

    def get_topic(self, arn):
        return self.topics[arn]

    def set_topic_attribute(self, topic_arn, attribute_name, attribute_value):
        topic = self.get_topic(topic_arn)
        setattr(topic, attribute_name, attribute_value)

    def subscribe(self, topic_arn, endpoint, protocol):
        topic = self.get_topic(topic_arn)
        subscription = Subscription(topic, endpoint, protocol)
        self.subscriptions[subscription.arn] = subscription
        return subscription

    def unsubscribe(self, subscription_arn):
        self.subscriptions.pop(subscription_arn)

    def list_subscriptions(self, topic_arn=None):
        if topic_arn:
            topic = self.get_topic(topic_arn)
            return [sub for sub in self.subscriptions.values() if sub.topic == topic]
        else:
            return self.subscriptions.values()

    def publish(self, topic_arn, message):
        topic = self.get_topic(topic_arn)
        message_id = topic.publish(message)
        return message_id


sns_backend = SNSBackend()


DEFAULT_TOPIC_POLICY = {
    "Version": "2008-10-17",
    "Id": "us-east-1/698519295917/test__default_policy_ID",
    "Statement": [{
        "Effect": "Allow",
        "Sid": "us-east-1/698519295917/test__default_statement_ID",
        "Principal": {
            "AWS": "*"
        },
        "Action": [
            "SNS:GetTopicAttributes",
            "SNS:SetTopicAttributes",
            "SNS:AddPermission",
            "SNS:RemovePermission",
            "SNS:DeleteTopic",
            "SNS:Subscribe",
            "SNS:ListSubscriptionsByTopic",
            "SNS:Publish",
            "SNS:Receive",
        ],
        "Resource": "arn:aws:sns:us-east-1:698519295917:test",
        "Condition": {
            "StringLike": {
                "AWS:SourceArn": "arn:aws:*:*:698519295917:*"
            }
        }
    }]
}

DEFAULT_EFFECTIVE_DELIVERY_POLICY = {
    'http': {
        'disableSubscriptionOverrides': False,
        'defaultHealthyRetryPolicy': {
            'numNoDelayRetries': 0,
            'numMinDelayRetries': 0,
            'minDelayTarget': 20,
            'maxDelayTarget': 20,
            'numMaxDelayRetries': 0,
            'numRetries': 3,
            'backoffFunction': 'linear'
        }
    }
}

########NEW FILE########
__FILENAME__ = responses
import json

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import sns_backend


class SNSResponse(BaseResponse):

    def create_topic(self):
        name = self._get_param('Name')
        topic = sns_backend.create_topic(name)

        return json.dumps({
            'CreateTopicResponse': {
                'CreateTopicResult': {
                    'TopicArn': topic.arn,
                },
                'ResponseMetadata': {
                    'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
                }
            }
        })

    def list_topics(self):
        topics = sns_backend.list_topics()

        return json.dumps({
            'ListTopicsResponse': {
                'ListTopicsResult': {
                    'Topics': [{'TopicArn': topic.arn} for topic in topics]
                }
            },
            'ResponseMetadata': {
                'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
            }
        })

    def delete_topic(self):
        topic_arn = self._get_param('TopicArn')
        sns_backend.delete_topic(topic_arn)

        return json.dumps({
            'DeleteTopicResponse': {
                'ResponseMetadata': {
                    'RequestId': 'a8dec8b3-33a4-11df-8963-01868b7c937a',
                }
            }
        })

    def get_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        topic = sns_backend.get_topic(topic_arn)

        return json.dumps({
            "GetTopicAttributesResponse": {
                "GetTopicAttributesResult": {
                    "Attributes": {
                        "Owner": topic.account_id,
                        "Policy": topic.policy,
                        "TopicArn": topic.arn,
                        "DisplayName": topic.display_name,
                        "SubscriptionsPending": topic.subscriptions_pending,
                        "SubscriptionsConfirmed": topic.subscriptions_confimed,
                        "SubscriptionsDeleted": topic.subscriptions_deleted,
                        "DeliveryPolicy": topic.delivery_policy,
                        "EffectiveDeliveryPolicy": topic.effective_delivery_policy,
                    }
                },
                "ResponseMetadata": {
                    "RequestId": "057f074c-33a7-11df-9540-99d0768312d3"
                }
            }
        })

    def set_topic_attributes(self):
        topic_arn = self._get_param('TopicArn')
        attribute_name = self._get_param('AttributeName')
        attribute_name = camelcase_to_underscores(attribute_name)
        attribute_value = self._get_param('AttributeValue')
        sns_backend.set_topic_attribute(topic_arn, attribute_name, attribute_value)

        return json.dumps({
            "SetTopicAttributesResponse": {
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def subscribe(self):
        topic_arn = self._get_param('TopicArn')
        endpoint = self._get_param('Endpoint')
        protocol = self._get_param('Protocol')
        subscription = sns_backend.subscribe(topic_arn, endpoint, protocol)

        return json.dumps({
            "SubscribeResponse": {
                "SubscribeResult": {
                    "SubscriptionArn": subscription.arn,
                },
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def unsubscribe(self):
        subscription_arn = self._get_param('SubscriptionArn')
        sns_backend.unsubscribe(subscription_arn)

        return json.dumps({
            "UnsubscribeResponse": {
                "ResponseMetadata": {
                    "RequestId": "a8763b99-33a7-11df-a9b7-05d48da6f042"
                }
            }
        })

    def list_subscriptions(self):
        subscriptions = sns_backend.list_subscriptions()

        return json.dumps({
            "ListSubscriptionsResponse": {
                "ListSubscriptionsResult": {
                    "Subscriptions": [{
                        "TopicArn": subscription.topic.arn,
                        "Protocol": subscription.protocol,
                        "SubscriptionArn": subscription.arn,
                        "Owner": subscription.topic.account_id,
                        "Endpoint": subscription.endpoint,
                    } for subscription in subscriptions]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def list_subscriptions_by_topic(self):
        topic_arn = self._get_param('TopicArn')
        subscriptions = sns_backend.list_subscriptions(topic_arn)

        return json.dumps({
            "ListSubscriptionsByTopicResponse": {
                "ListSubscriptionsByTopicResult": {
                    "Subscriptions": [{
                        "TopicArn": subscription.topic.arn,
                        "Protocol": subscription.protocol,
                        "SubscriptionArn": subscription.arn,
                        "Owner": subscription.topic.account_id,
                        "Endpoint": subscription.endpoint,
                    } for subscription in subscriptions]
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

    def publish(self):
        topic_arn = self._get_param('TopicArn')
        message = self._get_param('Message')
        message_id = sns_backend.publish(topic_arn, message)

        return json.dumps({
            "PublishResponse": {
                "PublishResult": {
                    "MessageId": message_id,
                },
                "ResponseMetadata": {
                    "RequestId": "384ac68d-3775-11df-8963-01868b7c937a",
                }
            }
        })

########NEW FILE########
__FILENAME__ = urls
from .responses import SNSResponse

url_bases = [
    "https?://sns.(.+).amazonaws.com"
]

url_paths = {
    '{0}/$': SNSResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import uuid


def make_arn_for_topic(account_id, name):
    return "arn:aws:sns:us-east-1:{0}:{1}".format(account_id, name)


def make_arn_for_subscription(topic_arn):
    subscription_id = uuid.uuid4()
    return "{0}:{1}".format(topic_arn, subscription_id)

########NEW FILE########
__FILENAME__ = models
import hashlib
import time
import re

from moto.core import BaseBackend
from moto.core.utils import camelcase_to_underscores, get_random_message_id
from .utils import generate_receipt_handle


class Message(object):

    def __init__(self, message_id, body):
        self.id = message_id
        self.body = body
        self.receipt_handle = generate_receipt_handle()

    @property
    def md5(self):
        body_md5 = hashlib.md5()
        body_md5.update(self.body)
        return body_md5.hexdigest()


class Queue(object):
    camelcase_attributes = ['ApproximateNumberOfMessages',
                            'ApproximateNumberOfMessagesDelayed',
                            'ApproximateNumberOfMessagesNotVisible',
                            'CreatedTimestamp',
                            'DelaySeconds',
                            'LastModifiedTimestamp',
                            'MaximumMessageSize',
                            'MessageRetentionPeriod',
                            'QueueArn',
                            'ReceiveMessageWaitTimeSeconds',
                            'VisibilityTimeout']

    def __init__(self, name, visibility_timeout):
        self.name = name
        self.visibility_timeout = visibility_timeout or 30
        self.messages = []

        now = time.time()

        self.approximate_number_of_messages_delayed = 0
        self.approximate_number_of_messages_not_visible = 0
        self.created_timestamp = now
        self.delay_seconds = 0
        self.last_modified_timestamp = now
        self.maximum_message_size = 64 << 10
        self.message_retention_period = 86400 * 4  # four days
        self.queue_arn = 'arn:aws:sqs:sqs.us-east-1:123456789012:%s' % self.name
        self.receive_message_wait_time_seconds = 0

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json):
        properties = cloudformation_json['Properties']

        return sqs_backend.create_queue(
            name=properties['QueueName'],
            visibility_timeout=properties.get('VisibilityTimeout'),
        )

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def attributes(self):
        result = {}
        for attribute in self.camelcase_attributes:
            result[attribute] = getattr(self, camelcase_to_underscores(attribute))
        return result

    @property
    def approximate_number_of_messages(self):
        return len(self.messages)


class SQSBackend(BaseBackend):

    def __init__(self):
        self.queues = {}
        super(SQSBackend, self).__init__()

    def create_queue(self, name, visibility_timeout):
        queue = Queue(name, visibility_timeout)
        self.queues[name] = queue
        return queue

    def list_queues(self, queue_name_prefix):
        re_str = '.*'
        if queue_name_prefix:
            re_str = '^{0}.*'.format(queue_name_prefix)
        prefix_re = re.compile(re_str)
        qs = []
        for name, q in self.queues.items():
            if prefix_re.search(name):
                qs.append(q)
        return qs

    def get_queue(self, queue_name):
        return self.queues.get(queue_name, None)

    def delete_queue(self, queue_name):
        if queue_name in self.queues:
            return self.queues.pop(queue_name)
        return False

    def set_queue_attribute(self, queue_name, key, value):
        queue = self.get_queue(queue_name)
        setattr(queue, key, value)
        return queue

    def send_message(self, queue_name, message_body, delay_seconds=None):
        # TODO impemented delay_seconds
        queue = self.get_queue(queue_name)
        message_id = get_random_message_id()
        message = Message(message_id, message_body)
        queue.messages.append(message)
        return message

    def receive_messages(self, queue_name, count):
        queue = self.get_queue(queue_name)
        result = []
        for _ in range(count):
            if queue.messages:
                result.append(queue.messages.pop(0))
        return result

    def delete_message(self, queue_name, receipt_handle):
        queue = self.get_queue(queue_name)
        new_messages = [
            message for message in queue.messages
            if message.receipt_handle != receipt_handle
        ]
        queue.message = new_messages


sqs_backend = SQSBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import sqs_backend


class QueuesResponse(BaseResponse):

    def create_queue(self):
        visibility_timeout = None
        if 'Attribute.1.Name' in self.querystring and self.querystring.get('Attribute.1.Name')[0] == 'VisibilityTimeout':
            visibility_timeout = self.querystring.get("Attribute.1.Value")[0]

        queue_name = self.querystring.get("QueueName")[0]
        queue = sqs_backend.create_queue(queue_name, visibility_timeout=visibility_timeout)
        template = Template(CREATE_QUEUE_RESPONSE)
        return template.render(queue=queue)

    def get_queue_url(self):
        queue_name = self.querystring.get("QueueName")[0]
        queue = sqs_backend.get_queue(queue_name)
        if queue:
            template = Template(GET_QUEUE_URL_RESPONSE)
            return template.render(queue=queue)
        else:
            return "", dict(status=404)

    def list_queues(self):
        queue_name_prefix = self.querystring.get("QueueNamePrefix", [None])[0]
        queues = sqs_backend.list_queues(queue_name_prefix)
        template = Template(LIST_QUEUES_RESPONSE)
        return template.render(queues=queues)


class QueueResponse(BaseResponse):
    def get_queue_attributes(self):
        queue_name = self.path.split("/")[-1]
        queue = sqs_backend.get_queue(queue_name)
        template = Template(GET_QUEUE_ATTRIBUTES_RESPONSE)
        return template.render(queue=queue)

    def set_queue_attributes(self):
        queue_name = self.path.split("/")[-1]
        key = camelcase_to_underscores(self.querystring.get('Attribute.Name')[0])
        value = self.querystring.get('Attribute.Value')[0]
        sqs_backend.set_queue_attribute(queue_name, key, value)
        return SET_QUEUE_ATTRIBUTE_RESPONSE

    def delete_queue(self):
        queue_name = self.path.split("/")[-1]
        queue = sqs_backend.delete_queue(queue_name)
        if not queue:
            return "A queue with name {0} does not exist".format(queue_name), dict(status=404)
        template = Template(DELETE_QUEUE_RESPONSE)
        return template.render(queue=queue)

    def send_message(self):
        message = self.querystring.get("MessageBody")[0]
        queue_name = self.path.split("/")[-1]
        message = sqs_backend.send_message(queue_name, message)
        template = Template(SEND_MESSAGE_RESPONSE)
        return template.render(message=message)

    def send_message_batch(self):
        """
        The querystring comes like this

        'SendMessageBatchRequestEntry.1.DelaySeconds': ['0'],
        'SendMessageBatchRequestEntry.1.MessageBody': ['test message 1'],
        'SendMessageBatchRequestEntry.1.Id': ['6d0f122d-4b13-da2c-378f-e74244d8ad11']
        'SendMessageBatchRequestEntry.2.Id': ['ff8cbf59-70a2-c1cb-44c7-b7469f1ba390'],
        'SendMessageBatchRequestEntry.2.MessageBody': ['test message 2'],
        'SendMessageBatchRequestEntry.2.DelaySeconds': ['0'],
        """

        queue_name = self.path.split("/")[-1]

        messages = []
        for index in range(1, 11):
            # Loop through looking for messages
            message_key = 'SendMessageBatchRequestEntry.{0}.MessageBody'.format(index)
            message_body = self.querystring.get(message_key)
            if not message_body:
                # Found all messages
                break

            message_user_id_key = 'SendMessageBatchRequestEntry.{0}.Id'.format(index)
            message_user_id = self.querystring.get(message_user_id_key)[0]
            delay_key = 'SendMessageBatchRequestEntry.{0}.DelaySeconds'.format(index)
            delay_seconds = self.querystring.get(delay_key, [None])[0]
            message = sqs_backend.send_message(queue_name, message_body[0], delay_seconds=delay_seconds)
            message.user_id = message_user_id
            messages.append(message)

        template = Template(SEND_MESSAGE_BATCH_RESPONSE)
        return template.render(messages=messages)

    def delete_message(self):
        queue_name = self.path.split("/")[-1]
        receipt_handle = self.querystring.get("ReceiptHandle")[0]
        sqs_backend.delete_message(queue_name, receipt_handle)
        template = Template(DELETE_MESSAGE_RESPONSE)
        return template.render()

    def delete_message_batch(self):
        """
        The querystring comes like this

        'DeleteMessageBatchRequestEntry.1.Id': ['message_1'],
        'DeleteMessageBatchRequestEntry.1.ReceiptHandle': ['asdfsfs...'],
        'DeleteMessageBatchRequestEntry.2.Id': ['message_2'],
        'DeleteMessageBatchRequestEntry.2.ReceiptHandle': ['zxcvfda...'],
        ...
        """
        queue_name = self.path.split("/")[-1]

        message_ids = []
        for index in range(1, 11):
            # Loop through looking for messages
            receipt_key = 'DeleteMessageBatchRequestEntry.{0}.ReceiptHandle'.format(index)
            receipt_handle = self.querystring.get(receipt_key)
            if not receipt_handle:
                # Found all messages
                break

            sqs_backend.delete_message(queue_name, receipt_handle[0])

            message_user_id_key = 'DeleteMessageBatchRequestEntry.{0}.Id'.format(index)
            message_user_id = self.querystring.get(message_user_id_key)[0]
            message_ids.append(message_user_id)

        template = Template(DELETE_MESSAGE_BATCH_RESPONSE)
        return template.render(message_ids=message_ids)

    def receive_message(self):
        queue_name = self.path.split("/")[-1]
        message_count = int(self.querystring.get("MaxNumberOfMessages")[0])
        messages = sqs_backend.receive_messages(queue_name, message_count)
        template = Template(RECEIVE_MESSAGE_RESPONSE)
        return template.render(messages=messages)


CREATE_QUEUE_RESPONSE = """<CreateQueueResponse>
    <CreateQueueResult>
        <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
        <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
    </CreateQueueResult>
    <ResponseMetadata>
        <RequestId>
            7a62c49f-347e-4fc4-9331-6e8e7a96aa73
        </RequestId>
    </ResponseMetadata>
</CreateQueueResponse>"""

GET_QUEUE_URL_RESPONSE = """<GetQueueUrlResponse>
    <GetQueueUrlResult>
        <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
    </GetQueueUrlResult>
    <ResponseMetadata>
        <RequestId>470a6f13-2ed9-4181-ad8a-2fdea142988e</RequestId>
    </ResponseMetadata>
</GetQueueUrlResponse>"""

LIST_QUEUES_RESPONSE = """<ListQueuesResponse>
    <ListQueuesResult>
        {% for queue in queues %}
            <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
            <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
        {% endfor %}
    </ListQueuesResult>
    <ResponseMetadata>
        <RequestId>
            725275ae-0b9b-4762-b238-436d7c65a1ac
        </RequestId>
    </ResponseMetadata>
</ListQueuesResponse>"""

DELETE_QUEUE_RESPONSE = """<DeleteQueueResponse>
    <ResponseMetadata>
        <RequestId>
            6fde8d1e-52cd-4581-8cd9-c512f4c64223
        </RequestId>
    </ResponseMetadata>
</DeleteQueueResponse>"""

GET_QUEUE_ATTRIBUTES_RESPONSE = """<GetQueueAttributesResponse>
  <GetQueueAttributesResult>
    {% for key, value in queue.attributes.items() %}
        <Attribute>
          <Name>{{ key }}</Name>
          <Value>{{ value }}</Value>
        </Attribute>
    {% endfor %}
  </GetQueueAttributesResult>
  <ResponseMetadata>
    <RequestId>1ea71be5-b5a2-4f9d-b85a-945d8d08cd0b</RequestId>
  </ResponseMetadata>
</GetQueueAttributesResponse>"""

SET_QUEUE_ATTRIBUTE_RESPONSE = """<SetQueueAttributesResponse>
    <ResponseMetadata>
        <RequestId>
            e5cca473-4fc0-4198-a451-8abb94d02c75
        </RequestId>
    </ResponseMetadata>
</SetQueueAttributesResponse>"""

SEND_MESSAGE_RESPONSE = """<SendMessageResponse>
    <SendMessageResult>
        <MD5OfMessageBody>
            {{ message.md5 }}
        </MD5OfMessageBody>
        <MessageId>
            {{ message.id }}
        </MessageId>
    </SendMessageResult>
    <ResponseMetadata>
        <RequestId>
            27daac76-34dd-47df-bd01-1f6e873584a0
        </RequestId>
    </ResponseMetadata>
</SendMessageResponse>"""

RECEIVE_MESSAGE_RESPONSE = """<ReceiveMessageResponse>
  <ReceiveMessageResult>
    {% for message in messages %}
        <Message>
          <MessageId>
            {{ message.id }}
          </MessageId>
          <ReceiptHandle>
            MbZj6wDWli+JvwwJaBV+3dcjk2YW2vA3+STFFljTM8tJJg6HRG6PYSasuWXPJB+Cw
            Lj1FjgXUv1uSj1gUPAWV66FU/WeR4mq2OKpEGYWbnLmpRCJVAyeMjeU5ZBdtcQ+QE
            auMZc8ZRv37sIW2iJKq3M9MFx1YvV11A2x/KSbkJ0=
          </ReceiptHandle>
          <MD5OfBody>
            {{ message.md5 }}
          </MD5OfBody>
          <Body>{{ message.body }}</Body>
        </Message>
    {% endfor %}
  </ReceiveMessageResult>
  <ResponseMetadata>
    <RequestId>
      b6633655-283d-45b4-aee4-4e84e0ae6afa
    </RequestId>
  </ResponseMetadata>
</ReceiveMessageResponse>"""

SEND_MESSAGE_BATCH_RESPONSE = """<SendMessageBatchResponse>
<SendMessageBatchResult>
    {% for message in messages %}
        <SendMessageBatchResultEntry>
            <Id>{{ message.user_id }}</Id>
            <MessageId>{{ message.id }}</MessageId>
            <MD5OfMessageBody>{{ message.md5 }}</MD5OfMessageBody>
        </SendMessageBatchResultEntry>
    {% endfor %}
</SendMessageBatchResult>
<ResponseMetadata>
    <RequestId>ca1ad5d0-8271-408b-8d0f-1351bf547e74</RequestId>
</ResponseMetadata>
</SendMessageBatchResponse>"""

DELETE_MESSAGE_RESPONSE = """<DeleteMessageResponse>
    <ResponseMetadata>
        <RequestId>
            b5293cb5-d306-4a17-9048-b263635abe42
        </RequestId>
    </ResponseMetadata>
</DeleteMessageResponse>"""

DELETE_MESSAGE_BATCH_RESPONSE = """<DeleteMessageBatchResponse>
    <DeleteMessageBatchResult>
        {% for message_id in message_ids %}
            <DeleteMessageBatchResultEntry>
                <Id>{{ message_id }}</Id>
            </DeleteMessageBatchResultEntry>
        {% endfor %}
    </DeleteMessageBatchResult>
    <ResponseMetadata>
        <RequestId>d6f86b7a-74d1-4439-b43f-196a1e29cd85</RequestId>
    </ResponseMetadata>
</DeleteMessageBatchResponse>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import QueueResponse, QueuesResponse

url_bases = [
    "https?://(.*?)(queue|sqs)(.*?).amazonaws.com"
]

url_paths = {
    '{0}/$': QueuesResponse().dispatch,
    '{0}/(?P<account_id>\d+)/(?P<queue_name>[a-zA-Z0-9\-_]+)': QueueResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = utils
import random
import string


def generate_receipt_handle():
    # http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/ImportantIdentifiers.html#ImportantIdentifiers-receipt-handles
    length = 185
    return ''.join(random.choice(string.lowercase) for x in range(length))

########NEW FILE########
__FILENAME__ = models
import datetime
from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime


class Token(object):
    def __init__(self, duration, name=None, policy=None):
        now = datetime.datetime.now()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.name = name
        self.policy = None

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime(self.expiration)


class AssumedRole(object):
    def __init__(self, role_session_name, role_arn, policy, duration, external_id):
        self.session_name = role_session_name
        self.arn = role_arn
        self.policy = policy
        now = datetime.datetime.now()
        self.expiration = now + datetime.timedelta(seconds=duration)
        self.external_id = external_id

    @property
    def expiration_ISO8601(self):
        return iso_8601_datetime(self.expiration)


class STSBackend(BaseBackend):
    def get_session_token(self, duration):
        token = Token(duration=duration)
        return token

    def get_federation_token(self, name, duration, policy):
        token = Token(duration=duration, name=name, policy=policy)
        return token

    def assume_role(self, **kwargs):
        role = AssumedRole(**kwargs)
        return role

sts_backend = STSBackend()

########NEW FILE########
__FILENAME__ = responses
from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import sts_backend


class TokenResponse(BaseResponse):

    def get_session_token(self):
        duration = int(self.querystring.get('DurationSeconds', [43200])[0])
        token = sts_backend.get_session_token(duration=duration)
        template = Template(GET_SESSION_TOKEN_RESPONSE)
        return template.render(token=token)

    def get_federation_token(self):
        duration = int(self.querystring.get('DurationSeconds', [43200])[0])
        policy = self.querystring.get('Policy', [None])[0]
        name = self.querystring.get('Name')[0]
        token = sts_backend.get_federation_token(
            duration=duration, name=name, policy=policy)
        template = Template(GET_FEDERATION_TOKEN_RESPONSE)
        return template.render(token=token)

    def assume_role(self):
        role_session_name = self.querystring.get('RoleSessionName')[0]
        role_arn = self.querystring.get('RoleArn')[0]

        policy = self.querystring.get('Policy', [None])[0]
        duration = int(self.querystring.get('DurationSeconds', [3600])[0])
        external_id = self.querystring.get('ExternalId', [None])[0]

        role = sts_backend.assume_role(
            role_session_name=role_session_name,
            role_arn=role_arn,
            policy=policy,
            duration=duration,
            external_id=external_id,
        )
        template = Template(ASSUME_ROLE_RESPONSE)
        return template.render(role=role)


GET_SESSION_TOKEN_RESPONSE = """<GetSessionTokenResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetSessionTokenResult>
    <Credentials>
      <SessionToken>AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE</SessionToken>
      <SecretAccessKey>wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY</SecretAccessKey>
      <Expiration>{{ token.expiration_ISO8601 }}</Expiration>
      <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
    </Credentials>
  </GetSessionTokenResult>
  <ResponseMetadata>
    <RequestId>58c5dbae-abef-11e0-8cfe-09039844ac7d</RequestId>
  </ResponseMetadata>
</GetSessionTokenResponse>"""


GET_FEDERATION_TOKEN_RESPONSE = """<GetFederationTokenResponse xmlns="https://sts.amazonaws.com/doc/
2011-06-15/">
  <GetFederationTokenResult>
    <Credentials>
      <SessionToken>AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA==</SessionToken>
      <SecretAccessKey>wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY</SecretAccessKey>
      <Expiration>{{ token.expiration_ISO8601 }}</Expiration>
      <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
    </Credentials>
    <FederatedUser>
      <Arn>arn:aws:sts::123456789012:federated-user/{{ token.name }}</Arn>
      <FederatedUserId>123456789012:{{ token.name }}</FederatedUserId>
    </FederatedUser>
    <PackedPolicySize>6</PackedPolicySize>
  </GetFederationTokenResult>
  <ResponseMetadata>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
  </ResponseMetadata>
</GetFederationTokenResponse>"""


ASSUME_ROLE_RESPONSE = """<AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/
2011-06-15/">
  <AssumeRoleResult>
    <Credentials>
      <SessionToken>BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE</SessionToken>
      <SecretAccessKey>aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY</SecretAccessKey>
      <Expiration>{{ role.expiration_ISO8601 }}</Expiration>
      <AccessKeyId>AKIAIOSFODNN7EXAMPLE</AccessKeyId>
    </Credentials>
    <AssumedRoleUser>
      <Arn>{{ role.arn }}</Arn>
      <AssumedRoleId>ARO123EXAMPLE123:{{ role.session_name }}</AssumedRoleId>
    </AssumedRoleUser>
    <PackedPolicySize>6</PackedPolicySize>
  </AssumeRoleResult>
  <ResponseMetadata>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
  </ResponseMetadata>
</AssumeRoleResponse>"""

########NEW FILE########
__FILENAME__ = urls
from .responses import TokenResponse

url_bases = [
    "https?://sts.amazonaws.com"
]

url_paths = {
    '{0}/$': TokenResponse().dispatch,
}

########NEW FILE########
__FILENAME__ = helpers
import boto
from nose.plugins.skip import SkipTest


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


class requires_boto_gte(object):
    """Decorator for requiring boto version greater than or equal to 'version'"""
    def __init__(self, version):
        self.version = version

    def __call__(self, test):
        boto_version = version_tuple(boto.__version__)
        required = version_tuple(self.version)
        if boto_version >= required:
            return test
        raise SkipTest

########NEW FILE########
__FILENAME__ = test_autoscaling
import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
import sure  # noqa

from moto import mock_autoscaling, mock_ec2
from tests.helpers import requires_boto_gte


@mock_autoscaling
def test_create_autoscaling_group():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        default_cooldown=60,
        desired_capacity=2,
        health_check_period=100,
        health_check_type="EC2",
        max_size=2,
        min_size=2,
        launch_config=config,
        load_balancers=["test_lb"],
        placement_group="test_placement",
        vpc_zone_identifier='subnet-1234abcd',
        termination_policies=["OldestInstance", "NewestInstance"],
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal('tester_group')
    set(group.availability_zones).should.equal(set(['us-east-1c', 'us-east-1b']))
    group.desired_capacity.should.equal(2)
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.vpc_zone_identifier.should.equal('subnet-1234abcd')
    group.launch_config_name.should.equal('tester')
    group.default_cooldown.should.equal(60)
    group.health_check_period.should.equal(100)
    group.health_check_type.should.equal("EC2")
    list(group.load_balancers).should.equal(["test_lb"])
    group.placement_group.should.equal("test_placement")
    list(group.termination_policies).should.equal(["OldestInstance", "NewestInstance"])


@mock_autoscaling
def test_create_autoscaling_groups_defaults():
    """ Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes """
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal('tester_group')
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.launch_config_name.should.equal('tester')

    # Defaults
    list(group.availability_zones).should.equal([])
    group.desired_capacity.should.equal(2)
    group.vpc_zone_identifier.should.equal('')
    group.default_cooldown.should.equal(300)
    group.health_check_period.should.equal(None)
    group.health_check_type.should.equal("EC2")
    list(group.load_balancers).should.equal([])
    group.placement_group.should.equal(None)
    list(group.termination_policies).should.equal([])


@mock_autoscaling
def test_autoscaling_group_describe_filter():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)
    group.name = 'tester_group2'
    conn.create_auto_scaling_group(group)
    group.name = 'tester_group3'
    conn.create_auto_scaling_group(group)

    conn.get_all_groups(names=['tester_group', 'tester_group2']).should.have.length_of(2)
    conn.get_all_groups().should.have.length_of(3)


@mock_autoscaling
def test_autoscaling_update():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.vpc_zone_identifier.should.equal('subnet-1234abcd')

    group.vpc_zone_identifier = 'subnet-5678efgh'
    group.update()

    group = conn.get_all_groups()[0]
    group.vpc_zone_identifier.should.equal('subnet-5678efgh')


@mock_autoscaling
def test_autoscaling_group_delete():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)

    conn.get_all_groups().should.have.length_of(1)

    conn.delete_auto_scaling_group('tester_group')
    conn.get_all_groups().should.have.length_of(0)


@mock_ec2
@mock_autoscaling
def test_autoscaling_group_describe_instances():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)
    instances[0].launch_config_name.should.equal('tester')
    autoscale_instance_ids = [instance.instance_id for instance in instances]

    ec2_conn = boto.connect_ec2()
    reservations = ec2_conn.get_all_instances()
    instances = reservations[0].instances
    instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in instances]
    set(autoscale_instance_ids).should.equal(set(instance_ids))


@requires_boto_gte("2.8")
@mock_autoscaling
def test_set_desired_capacity_up():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 3)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(3)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@requires_boto_gte("2.8")
@mock_autoscaling
def test_set_desired_capacity_down():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 1)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(1)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(1)


@requires_boto_gte("2.8")
@mock_autoscaling
def test_set_desired_capacity_the_same():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 2)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

########NEW FILE########
__FILENAME__ = test_launch_configurations
import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping

import sure  # noqa

from moto import mock_autoscaling
from tests.helpers import requires_boto_gte


@mock_autoscaling
def test_create_launch_configuration():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
        key_name='the_keys',
        security_groups=["default", "default2"],
        user_data="This is some user_data",
        instance_monitoring=True,
        instance_profile_name='arn:aws:iam::123456789012:instance-profile/testing',
        spot_price=0.1,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('m1.small')
    launch_config.key_name.should.equal('the_keys')
    set(launch_config.security_groups).should.equal(set(['default', 'default2']))
    launch_config.user_data.should.equal("This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal('true')
    launch_config.instance_profile_name.should.equal('arn:aws:iam::123456789012:instance-profile/testing')
    launch_config.spot_price.should.equal(0.1)


@requires_boto_gte("2.27.0")
@mock_autoscaling
def test_create_launch_configuration_with_block_device_mappings():
    block_device_mapping = BlockDeviceMapping()

    ephemeral_drive = BlockDeviceType()
    ephemeral_drive.ephemeral_name = 'ephemeral0'
    block_device_mapping['/dev/xvdb'] = ephemeral_drive

    snapshot_drive = BlockDeviceType()
    snapshot_drive.snapshot_id = "snap-1234abcd"
    snapshot_drive.volume_type = "standard"
    block_device_mapping['/dev/xvdp'] = snapshot_drive

    ebs_drive = BlockDeviceType()
    ebs_drive.volume_type = "io1"
    ebs_drive.size = 100
    ebs_drive.iops = 1000
    ebs_drive.delete_on_termination = False
    block_device_mapping['/dev/xvdh'] = ebs_drive

    conn = boto.connect_autoscale(use_block_device_types=True)
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
        key_name='the_keys',
        security_groups=["default", "default2"],
        user_data="This is some user_data",
        instance_monitoring=True,
        instance_profile_name='arn:aws:iam::123456789012:instance-profile/testing',
        spot_price=0.1,
        block_device_mappings=[block_device_mapping]
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('m1.small')
    launch_config.key_name.should.equal('the_keys')
    set(launch_config.security_groups).should.equal(set(['default', 'default2']))
    launch_config.user_data.should.equal("This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal('true')
    launch_config.instance_profile_name.should.equal('arn:aws:iam::123456789012:instance-profile/testing')
    launch_config.spot_price.should.equal(0.1)
    len(launch_config.block_device_mappings).should.equal(3)

    returned_mapping = launch_config.block_device_mappings

    set(returned_mapping.keys()).should.equal(set(['/dev/xvdb', '/dev/xvdp', '/dev/xvdh']))

    returned_mapping['/dev/xvdh'].iops.should.equal(1000)
    returned_mapping['/dev/xvdh'].size.should.equal(100)
    returned_mapping['/dev/xvdh'].volume_type.should.equal("io1")
    returned_mapping['/dev/xvdh'].delete_on_termination.should.be.false

    returned_mapping['/dev/xvdp'].snapshot_id.should.equal("snap-1234abcd")
    returned_mapping['/dev/xvdp'].volume_type.should.equal("standard")

    returned_mapping['/dev/xvdb'].ephemeral_name.should.equal('ephemeral0')


@requires_boto_gte("2.12")
@mock_autoscaling
def test_create_launch_configuration_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        ebs_optimized=True,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(True)


@requires_boto_gte("2.25.0")
@mock_autoscaling
def test_create_launch_configuration_using_ip_association():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        associate_public_ip_address=True,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.associate_public_ip_address.should.equal(True)


@requires_boto_gte("2.25.0")
@mock_autoscaling
def test_create_launch_configuration_using_ip_association_should_default_to_false():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.associate_public_ip_address.should.equal(False)



@mock_autoscaling
def test_create_launch_configuration_defaults():
    """ Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes """
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('m1.small')

    # Defaults
    launch_config.key_name.should.equal('')
    list(launch_config.security_groups).should.equal([])
    launch_config.user_data.should.equal("")
    launch_config.instance_monitoring.enabled.should.equal('false')
    launch_config.instance_profile_name.should.equal(None)
    launch_config.spot_price.should.equal(None)
    launch_config.ebs_optimized.should.equal(False)


@requires_boto_gte("2.12")
@mock_autoscaling
def test_create_launch_configuration_defaults_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(False)


@mock_autoscaling
def test_launch_configuration_describe_filter():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)
    config.name = 'tester2'
    conn.create_launch_configuration(config)
    config.name = 'tester3'
    conn.create_launch_configuration(config)

    conn.get_all_launch_configurations(names=['tester', 'tester2']).should.have.length_of(2)
    conn.get_all_launch_configurations().should.have.length_of(3)


@mock_autoscaling
def test_launch_configuration_delete():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    conn.get_all_launch_configurations().should.have.length_of(1)

    conn.delete_launch_configuration('tester')
    conn.get_all_launch_configurations().should.have.length_of(0)

########NEW FILE########
__FILENAME__ = test_policies
import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale.policy import ScalingPolicy
import sure  # noqa

from moto import mock_autoscaling


def setup_autoscale_group():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)
    return group


@mock_autoscaling
def test_create_policy():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ExactCapacity',
        as_name='tester_group',
        scaling_adjustment=3,
        cooldown=60,
    )
    conn.create_scaling_policy(policy)

    policy = conn.get_all_policies()[0]
    policy.name.should.equal('ScaleUp')
    policy.adjustment_type.should.equal('ExactCapacity')
    policy.as_name.should.equal('tester_group')
    policy.scaling_adjustment.should.equal(3)
    policy.cooldown.should.equal(60)


@mock_autoscaling
def test_create_policy_default_values():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ExactCapacity',
        as_name='tester_group',
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    policy = conn.get_all_policies()[0]
    policy.name.should.equal('ScaleUp')

    # Defaults
    policy.cooldown.should.equal(300)


@mock_autoscaling
def test_update_policy():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ExactCapacity',
        as_name='tester_group',
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    policy = conn.get_all_policies()[0]
    policy.scaling_adjustment.should.equal(3)

    # Now update it by creating another with the same name
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ExactCapacity',
        as_name='tester_group',
        scaling_adjustment=2,
    )
    conn.create_scaling_policy(policy)
    policy = conn.get_all_policies()[0]
    policy.scaling_adjustment.should.equal(2)


@mock_autoscaling
def test_delete_policy():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ExactCapacity',
        as_name='tester_group',
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    conn.get_all_policies().should.have.length_of(1)

    conn.delete_policy('ScaleUp')
    conn.get_all_policies().should.have.length_of(0)


@mock_autoscaling
def test_execute_policy_exact_capacity():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ExactCapacity',
        as_name='tester_group',
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@mock_autoscaling
def test_execute_policy_positive_change_in_capacity():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='ChangeInCapacity',
        as_name='tester_group',
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(5)


@mock_autoscaling
def test_execute_policy_percent_change_in_capacity():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='PercentChangeInCapacity',
        as_name='tester_group',
        scaling_adjustment=50,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@mock_autoscaling
def test_execute_policy_small_percent_change_in_capacity():
    """ http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
    If PercentChangeInCapacity returns a value between 0 and 1,
    Auto Scaling will round it off to 1."""
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name='ScaleUp',
        adjustment_type='PercentChangeInCapacity',
        as_name='tester_group',
        scaling_adjustment=1,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_describe_autoscaling_groups():
    backend = server.create_backend_app("autoscaling")
    test_client = backend.test_client()

    res = test_client.get('/?Action=DescribeLaunchConfigurations')

    res.data.should.contain('<DescribeLaunchConfigurationsResponse')
    res.data.should.contain('<LaunchConfigurations>')

########NEW FILE########
__FILENAME__ = single_instance_with_ebs_volume
template = {
    "Description": "AWS CloudFormation Sample Template Gollum_Single_Instance_With_EBS_Volume: Gollum is a simple wiki system built on top of Git that powers GitHub Wikis. This template installs a Gollum Wiki stack on a single EC2 instance with an EBS volume for storage and demonstrates using the AWS CloudFormation bootstrap scripts to install the packages and files necessary at instance launch time. **WARNING** This template creates an Amazon EC2 instance and an EBS volume. You will be billed for the AWS resources used if you create a stack from this template.",
    "Parameters": {
        "SSHLocation": {
            "ConstraintDescription": "must be a valid IP CIDR range of the form x.x.x.x/x.",
            "Description": "The IP address range that can be used to SSH to the EC2 instances",
            "Default": "0.0.0.0/0",
            "MinLength": "9",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "MaxLength": "18",
            "Type": "String"
        },
        "KeyName": {
            "Type": "String",
            "Description": "Name of an existing EC2 KeyPair to enable SSH access to the instances",
            "MinLength": "1",
            "AllowedPattern": "[\\x20-\\x7E]*",
            "MaxLength": "255",
            "ConstraintDescription": "can contain only ASCII characters."
        },
        "InstanceType": {
            "Default": "m1.small",
            "ConstraintDescription": "must be a valid EC2 instance type.",
            "Type": "String",
            "Description": "WebServer EC2 instance type",
            "AllowedValues": [
                "t1.micro",
                "m1.small",
                "m1.medium",
                "m1.large",
                "m1.xlarge",
                "m2.xlarge",
                "m2.2xlarge",
                "m2.4xlarge",
                "m3.xlarge",
                "m3.2xlarge",
                "c1.medium",
                "c1.xlarge",
                "cc1.4xlarge",
                "cc2.8xlarge",
                "cg1.4xlarge"
            ]
        },
        "VolumeSize": {
            "Description": "WebServer EC2 instance type",
            "Default": "5",
            "Type": "Number",
            "MaxValue": "1024",
            "MinValue": "5",
            "ConstraintDescription": "must be between 5 and 1024 Gb."
        }
    },
    "AWSTemplateFormatVersion": "2010-09-09",
    "Outputs": {
        "WebsiteURL": {
            "Description": "URL for Gollum wiki",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        "http://",
                        {
                            "Fn::GetAtt": [
                                "WebServer",
                                "PublicDnsName"
                            ]
                        }
                    ]
                ]
            }
        }
    },
    "Resources": {
        "WebServerSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "SecurityGroupIngress": [
                    {
                        "ToPort": "80",
                        "IpProtocol": "tcp",
                        "CidrIp": "0.0.0.0/0",
                        "FromPort": "80"
                    },
                    {
                        "ToPort": "22",
                        "IpProtocol": "tcp",
                        "CidrIp": {
                            "Ref": "SSHLocation"
                        },
                        "FromPort": "22"
                    }
                ],
                "GroupDescription": "Enable SSH access and HTTP access on the inbound port"
            }
        },
        "WebServer": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "UserData": {
                    "Fn::Base64": {
                        "Fn::Join": [
                            "",
                            [
                                "#!/bin/bash -v\n",
                                "yum update -y aws-cfn-bootstrap\n",
                                "# Helper function\n",
                                "function error_exit\n",
                                "{\n",
                                "  /opt/aws/bin/cfn-signal -e 1 -r \"$1\" '",
                                {
                                    "Ref": "WaitHandle"
                                },
                                "'\n",
                                "  exit 1\n",
                                "}\n",
                                "# Install Rails packages\n",
                                "/opt/aws/bin/cfn-init -s ",
                                {
                                    "Ref": "AWS::StackId"
                                },
                                " -r WebServer ",
                                "    --region ",
                                {
                                    "Ref": "AWS::Region"
                                },
                                " || error_exit 'Failed to run cfn-init'\n",
                                "# Wait for the EBS volume to show up\n",
                                "while [ ! -e /dev/sdh ]; do echo Waiting for EBS volume to attach; sleep 5; done\n",
                                "# Format the EBS volume and mount it\n",
                                "mkdir /var/wikidata\n",
                                "/sbin/mkfs -t ext3 /dev/sdh1\n",
                                "mount /dev/sdh1 /var/wikidata\n",
                                "# Initialize the wiki and fire up the server\n",
                                "cd /var/wikidata\n",
                                "git init\n",
                                "gollum --port 80 --host 0.0.0.0 &\n",
                                "# If all is well so signal success\n",
                                "/opt/aws/bin/cfn-signal -e $? -r \"Rails application setup complete\" '",
                                {
                                    "Ref": "WaitHandle"
                                },
                                "'\n"
                            ]
                        ]
                    }
                },
                "KeyName": {
                    "Ref": "KeyName"
                },
                "SecurityGroups": [
                    {
                        "Ref": "WebServerSecurityGroup"
                    }
                ],
                "InstanceType": {
                    "Ref": "InstanceType"
                },
                "ImageId": {
                    "Fn::FindInMap": [
                        "AWSRegionArch2AMI",
                        {
                            "Ref": "AWS::Region"
                        },
                        {
                            "Fn::FindInMap": [
                                "AWSInstanceType2Arch",
                                {
                                    "Ref": "InstanceType"
                                },
                                "Arch"
                            ]
                        }
                    ]
                }
            },
            "Metadata": {
                "AWS::CloudFormation::Init": {
                    "config": {
                        "packages": {
                            "rubygems": {
                                "nokogiri": [
                                    "1.5.10"
                                ],
                                "rdiscount": [],
                                "gollum": [
                                    "1.1.1"
                                ]
                            },
                            "yum": {
                                "libxslt-devel": [],
                                "gcc": [],
                                "git": [],
                                "rubygems": [],
                                "ruby-devel": [],
                                "ruby-rdoc": [],
                                "make": [],
                                "libxml2-devel": []
                            }
                        }
                    }
                }
            }
        },
        "DataVolume": {
            "Type": "AWS::EC2::Volume",
            "Properties": {
                "Tags": [
                    {
                        "Value": "Gollum Data Volume",
                        "Key": "Usage"
                    }
                ],
                "AvailabilityZone": {
                    "Fn::GetAtt": [
                        "WebServer",
                        "AvailabilityZone"
                    ]
                },
                "Size": "100",
            }
        },
        "MountPoint": {
            "Type": "AWS::EC2::VolumeAttachment",
            "Properties": {
                "InstanceId": {
                    "Ref": "WebServer"
                },
                "Device": "/dev/sdh",
                "VolumeId": {
                    "Ref": "DataVolume"
                }
            }
        },
        "WaitCondition": {
            "DependsOn": "MountPoint",
            "Type": "AWS::CloudFormation::WaitCondition",
            "Properties": {
                "Handle": {
                    "Ref": "WaitHandle"
                },
                "Timeout": "300"
            },
            "Metadata": {
                "Comment1": "Note that the WaitCondition is dependent on the volume mount point allowing the volume to be created and attached to the EC2 instance",
                "Comment2": "The instance bootstrap script waits for the volume to be attached to the instance prior to installing Gollum and signalling completion"
            }
        },
        "WaitHandle": {
            "Type": "AWS::CloudFormation::WaitConditionHandle"
        }
    },
    "Mappings": {
        "AWSInstanceType2Arch": {
            "m3.2xlarge": {
                "Arch": "64"
            },
            "m2.2xlarge": {
                "Arch": "64"
            },
            "m1.small": {
                "Arch": "64"
            },
            "c1.medium": {
                "Arch": "64"
            },
            "cg1.4xlarge": {
                "Arch": "64HVM"
            },
            "m2.xlarge": {
                "Arch": "64"
            },
            "t1.micro": {
                "Arch": "64"
            },
            "cc1.4xlarge": {
                "Arch": "64HVM"
            },
            "m1.medium": {
                "Arch": "64"
            },
            "cc2.8xlarge": {
                "Arch": "64HVM"
            },
            "m1.large": {
                "Arch": "64"
            },
            "m1.xlarge": {
                "Arch": "64"
            },
            "m2.4xlarge": {
                "Arch": "64"
            },
            "c1.xlarge": {
                "Arch": "64"
            },
            "m3.xlarge": {
                "Arch": "64"
            }
        },
        "AWSRegionArch2AMI": {
            "ap-southeast-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-b4b0cae6",
                "64": "ami-beb0caec"
            },
            "ap-southeast-2": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-b3990e89",
                "64": "ami-bd990e87"
            },
            "us-west-2": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-38fe7308",
                "64": "ami-30fe7300"
            },
            "us-east-1": {
                "64HVM": "ami-0da96764",
                "32": "ami-31814f58",
                "64": "ami-1b814f72"
            },
            "ap-northeast-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-0644f007",
                "64": "ami-0a44f00b"
            },
            "us-west-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-11d68a54",
                "64": "ami-1bd68a5e"
            },
            "eu-west-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-973b06e3",
                "64": "ami-953b06e1"
            },
            "sa-east-1": {
                "64HVM": "NOT_YET_SUPPORTED",
                "32": "ami-3e3be423",
                "64": "ami-3c3be421"
            }
        }
    }
}

########NEW FILE########
__FILENAME__ = vpc_single_instance_in_subnet
template = {
    "Description": "AWS CloudFormation Sample Template vpc_single_instance_in_subnet.template: Sample template showing how to create a VPC and add an EC2 instance with an Elastic IP address and a security group. **WARNING** This template creates an Amazon EC2 instance. You will be billed for the AWS resources used if you create a stack from this template.",
    "Parameters": {
        "SSHLocation": {
            "ConstraintDescription": "must be a valid IP CIDR range of the form x.x.x.x/x.",
            "Description": " The IP address range that can be used to SSH to the EC2 instances",
            "Default": "0.0.0.0/0",
            "MinLength": "9",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "MaxLength": "18",
            "Type": "String"
        },
        "KeyName": {
            "Type": "String",
            "Description": "Name of an existing EC2 KeyPair to enable SSH access to the instance",
            "MinLength": "1",
            "AllowedPattern": "[\\x20-\\x7E]*",
            "MaxLength": "255",
            "ConstraintDescription": "can contain only ASCII characters."
        },
        "InstanceType": {
            "Default": "m1.small",
            "ConstraintDescription": "must be a valid EC2 instance type.",
            "Type": "String",
            "Description": "WebServer EC2 instance type",
            "AllowedValues": [
                "t1.micro",
                "m1.small",
                "m1.medium",
                "m1.large",
                "m1.xlarge",
                "m2.xlarge",
                "m2.2xlarge",
                "m2.4xlarge",
                "m3.xlarge",
                "m3.2xlarge",
                "c1.medium",
                "c1.xlarge",
                "cc1.4xlarge",
                "cc2.8xlarge",
                "cg1.4xlarge"
            ]
        }
    },
    "AWSTemplateFormatVersion": "2010-09-09",
    "Outputs": {
        "URL": {
            "Description": "Newly created application URL",
            "Value": {
                "Fn::Join": [
                    "",
                    [
                        "http://",
                        {
                            "Fn::GetAtt": [
                                "WebServerInstance",
                                "PublicIp"
                            ]
                        }
                    ]
                ]
            }
        }
    },
    "Resources": {
        "Subnet": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {
                    "Ref": "VPC"
                },
                "CidrBlock": "10.0.0.0/24",
                "Tags": [
                    {
                        "Value": {
                            "Ref": "AWS::StackId"
                        },
                        "Key": "Application"
                    }
                ]
            }
        },
        "WebServerWaitHandle": {
            "Type": "AWS::CloudFormation::WaitConditionHandle"
        },
        "Route": {
            "Type": "AWS::EC2::Route",
            "Properties": {
                "GatewayId": {
                    "Ref": "InternetGateway"
                },
                "DestinationCidrBlock": "0.0.0.0/0",
                "RouteTableId": {
                    "Ref": "RouteTable"
                }
            },
            "DependsOn": "AttachGateway"
        },
        "SubnetRouteTableAssociation": {
            "Type": "AWS::EC2::SubnetRouteTableAssociation",
            "Properties": {
                "SubnetId": {
                    "Ref": "Subnet"
                },
                "RouteTableId": {
                    "Ref": "RouteTable"
                }
            }
        },
        "InternetGateway": {
            "Type": "AWS::EC2::InternetGateway",
            "Properties": {
                "Tags": [
                    {
                        "Value": {
                            "Ref": "AWS::StackId"
                        },
                        "Key": "Application"
                    }
                ]
            }
        },
        "RouteTable": {
            "Type": "AWS::EC2::RouteTable",
            "Properties": {
                "VpcId": {
                    "Ref": "VPC"
                },
                "Tags": [
                    {
                        "Value": {
                            "Ref": "AWS::StackId"
                        },
                        "Key": "Application"
                    }
                ]
            }
        },
        "WebServerWaitCondition": {
            "Type": "AWS::CloudFormation::WaitCondition",
            "Properties": {
                "Handle": {
                    "Ref": "WebServerWaitHandle"
                },
                "Timeout": "300"
            },
            "DependsOn": "WebServerInstance"
        },
        "VPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16",
                "Tags": [
                    {
                        "Value": {
                            "Ref": "AWS::StackId"
                        },
                        "Key": "Application"
                    }
                ]
            }
        },
        "InstanceSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "SecurityGroupIngress": [
                    {
                        "ToPort": "22",
                        "IpProtocol": "tcp",
                        "CidrIp": {
                            "Ref": "SSHLocation"
                        },
                        "FromPort": "22"
                    },
                    {
                        "ToPort": "80",
                        "IpProtocol": "tcp",
                        "CidrIp": "0.0.0.0/0",
                        "FromPort": "80"
                    }
                ],
                "VpcId": {
                    "Ref": "VPC"
                },
                "GroupDescription": "Enable SSH access via port 22"
            }
        },
        "WebServerInstance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "UserData": {
                    "Fn::Base64": {
                        "Fn::Join": [
                            "",
                            [
                                "#!/bin/bash\n",
                                "yum update -y aws-cfn-bootstrap\n",
                                "# Helper function\n",
                                "function error_exit\n",
                                "{\n",
                                "  /opt/aws/bin/cfn-signal -e 1 -r \"$1\" '",
                                {
                                    "Ref": "WebServerWaitHandle"
                                },
                                "'\n",
                                "  exit 1\n",
                                "}\n",
                                "# Install the simple web page\n",
                                "/opt/aws/bin/cfn-init -s ",
                                {
                                    "Ref": "AWS::StackId"
                                },
                                " -r WebServerInstance ",
                                "         --region ",
                                {
                                    "Ref": "AWS::Region"
                                },
                                " || error_exit 'Failed to run cfn-init'\n",
                                "# Start up the cfn-hup daemon to listen for changes to the Web Server metadata\n",
                                "/opt/aws/bin/cfn-hup || error_exit 'Failed to start cfn-hup'\n",
                                "# All done so signal success\n",
                                "/opt/aws/bin/cfn-signal -e 0 -r \"WebServer setup complete\" '",
                                {
                                    "Ref": "WebServerWaitHandle"
                                },
                                "'\n"
                            ]
                        ]
                    }
                },
                "Tags": [
                    {
                        "Value": {
                            "Ref": "AWS::StackId"
                        },
                        "Key": "Application"
                    }
                ],
                "SecurityGroupIds": [
                    {
                        "Ref": "InstanceSecurityGroup"
                    }
                ],
                "KeyName": {
                    "Ref": "KeyName"
                },
                "SubnetId": {
                    "Ref": "Subnet"
                },
                "ImageId": {
                    "Fn::FindInMap": [
                        "RegionMap",
                        {
                            "Ref": "AWS::Region"
                        },
                        "AMI"
                    ]
                },
                "InstanceType": {
                    "Ref": "InstanceType"
                }
            },
            "Metadata": {
                "Comment": "Install a simple PHP application",
                "AWS::CloudFormation::Init": {
                    "config": {
                        "files": {
                            "/etc/cfn/cfn-hup.conf": {
                                "content": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "[main]\n",
                                            "stack=",
                                            {
                                                "Ref": "AWS::StackId"
                                            },
                                            "\n",
                                            "region=",
                                            {
                                                "Ref": "AWS::Region"
                                            },
                                            "\n"
                                        ]
                                    ]
                                },
                                "owner": "root",
                                "group": "root",
                                "mode": "000400"
                            },
                            "/etc/cfn/hooks.d/cfn-auto-reloader.conf": {
                                "content": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "[cfn-auto-reloader-hook]\n",
                                            "triggers=post.update\n",
                                            "path=Resources.WebServerInstance.Metadata.AWS::CloudFormation::Init\n",
                                            "action=/opt/aws/bin/cfn-init -s ",
                                            {
                                                "Ref": "AWS::StackId"
                                            },
                                            " -r WebServerInstance ",
                                            " --region     ",
                                            {
                                                "Ref": "AWS::Region"
                                            },
                                            "\n",
                                            "runas=root\n"
                                        ]
                                    ]
                                }
                            },
                            "/var/www/html/index.php": {
                                "content": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "<?php\n",
                                            "echo '<h1>AWS CloudFormation sample PHP application</h1>';\n",
                                            "?>\n"
                                        ]
                                    ]
                                },
                                "owner": "apache",
                                "group": "apache",
                                "mode": "000644"
                            }
                        },
                        "services": {
                            "sysvinit": {
                                "httpd": {
                                    "ensureRunning": "true",
                                    "enabled": "true"
                                },
                                "sendmail": {
                                    "ensureRunning": "false",
                                    "enabled": "false"
                                }
                            }
                        },
                        "packages": {
                            "yum": {
                                "httpd": [],
                                "php": []
                            }
                        }
                    }
                }
            }
        },
        "IPAddress": {
            "Type": "AWS::EC2::EIP",
            "Properties": {
                "InstanceId": {
                    "Ref": "WebServerInstance"
                },
                "Domain": "vpc"
            },
            "DependsOn": "AttachGateway"
        },
        "AttachGateway": {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {
                    "Ref": "VPC"
                },
                "InternetGatewayId": {
                    "Ref": "InternetGateway"
                }
            }
        }
    },
    "Mappings": {
        "RegionMap": {
            "ap-southeast-1": {
                "AMI": "ami-74dda626"
            },
            "ap-southeast-2": {
                "AMI": "ami-b3990e89"
            },
            "us-west-2": {
                "AMI": "ami-16fd7026"
            },
            "us-east-1": {
                "AMI": "ami-7f418316"
            },
            "ap-northeast-1": {
                "AMI": "ami-dcfa4edd"
            },
            "us-west-1": {
                "AMI": "ami-951945d0"
            },
            "eu-west-1": {
                "AMI": "ami-24506250"
            },
            "sa-east-1": {
                "AMI": "ami-3e3be423"
            }
        }
    }
}

########NEW FILE########
__FILENAME__ = test_cloudformation_stack_crud
import json

import boto
import sure  # noqa

from moto import mock_cloudformation

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 1",
    "Resources": {},
}

dummy_template2 = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Stack 2",
    "Resources": {},
}

dummy_template_json = json.dumps(dummy_template)
dummy_template_json2 = json.dumps(dummy_template2)


@mock_cloudformation
def test_create_stack():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks()[0]
    stack.stack_name.should.equal('test_stack')
    stack.get_template().should.equal(dummy_template)


@mock_cloudformation
def test_describe_stack_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    stack = conn.describe_stacks("test_stack")[0]
    stack.stack_name.should.equal('test_stack')


@mock_cloudformation
def test_get_template_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    template = conn.get_template("test_stack")
    template.should.equal(dummy_template)


@mock_cloudformation
def test_list_stacks():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )
    conn.create_stack(
        "test_stack2",
        template_body=dummy_template_json,
    )

    stacks = conn.list_stacks()
    stacks.should.have.length_of(2)
    stacks[0].template_description.should.equal("Stack 1")


@mock_cloudformation
def test_delete_stack_by_name():
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack("test_stack")
    conn.list_stacks().should.have.length_of(0)


@mock_cloudformation
def test_delete_stack_by_id():
    conn = boto.connect_cloudformation()
    stack_id = conn.create_stack(
        "test_stack",
        template_body=dummy_template_json,
    )

    conn.list_stacks().should.have.length_of(1)
    conn.delete_stack(stack_id)
    conn.list_stacks().should.have.length_of(0)


# @mock_cloudformation
# def test_update_stack():
#     conn = boto.connect_cloudformation()
#     conn.create_stack(
#         "test_stack",
#         template_body=dummy_template_json,
#     )

#     conn.update_stack("test_stack", dummy_template_json2)

#     stack = conn.describe_stacks()[0]
#     stack.get_template().should.equal(dummy_template2)

########NEW FILE########
__FILENAME__ = test_cloudformation_stack_integration
import json

import boto
import sure  # noqa

from moto import (
    mock_autoscaling,
    mock_cloudformation,
    mock_ec2,
    mock_elb,
    mock_iam,
)

from .fixtures import single_instance_with_ebs_volume, vpc_single_instance_in_subnet


@mock_cloudformation()
def test_stack_sqs_integration():
    sqs_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "QueueGroup": {

                "Type": "AWS::SQS::Queue",
                "Properties": {
                    "QueueName": "my-queue",
                    "VisibilityTimeout": 60,
                }
            },
        },
    }
    sqs_template_json = json.dumps(sqs_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=sqs_template_json,
    )

    stack = conn.describe_stacks()[0]
    queue = stack.describe_resources()[0]
    queue.resource_type.should.equal('AWS::SQS::Queue')
    queue.logical_resource_id.should.equal("QueueGroup")
    queue.physical_resource_id.should.equal("my-queue")


@mock_ec2()
@mock_cloudformation()
def test_stack_ec2_integration():
    ec2_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "WebServerGroup": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": "ami-1234abcd",
                    "UserData": "some user data",
                }
            },
        },
    }
    ec2_template_json = json.dumps(ec2_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "ec2_stack",
        template_body=ec2_template_json,
    )

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    stack = conn.describe_stacks()[0]
    instance = stack.describe_resources()[0]
    instance.resource_type.should.equal('AWS::EC2::Instance')
    instance.logical_resource_id.should.equal("WebServerGroup")
    instance.physical_resource_id.should.equal(ec2_instance.id)


@mock_ec2()
@mock_elb()
@mock_cloudformation()
def test_stack_elb_integration_with_attached_ec2_instances():
    elb_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyELB": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Instances": [{"Ref": "Ec2Instance1"}],
                "Properties": {
                    "LoadBalancerName": "test-elb",
                    "AvailabilityZones": ['us-east1'],
                }
            },
            "Ec2Instance1": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": "ami-1234abcd",
                    "UserData": "some user data",
                }
            },
        },
    }
    elb_template_json = json.dumps(elb_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "elb_stack",
        template_body=elb_template_json,
    )

    elb_conn = boto.connect_elb()
    load_balancer = elb_conn.get_all_load_balancers()[0]

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]
    instance_id = ec2_instance.id

    load_balancer.instances[0].id.should.equal(ec2_instance.id)
    list(load_balancer.availability_zones).should.equal(['us-east1'])
    load_balancer_name = load_balancer.name

    stack = conn.describe_stacks()[0]
    stack_resources = stack.describe_resources()
    stack_resources.should.have.length_of(2)
    for resource in stack_resources:
        if resource.resource_type == 'AWS::ElasticLoadBalancing::LoadBalancer':
            load_balancer = resource
        else:
            ec2_instance = resource

    load_balancer.logical_resource_id.should.equal("MyELB")
    load_balancer.physical_resource_id.should.equal(load_balancer_name)
    ec2_instance.physical_resource_id.should.equal(instance_id)


@mock_ec2()
@mock_cloudformation()
def test_stack_security_groups():
    security_group_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "my-security-group": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "My other group",
                },
            },
            "Ec2Instance2": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "SecurityGroups": [{"Ref": "InstanceSecurityGroup"}],
                    "ImageId": "ami-1234abcd",
                }
            },
            "InstanceSecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "My security group",
                    "SecurityGroupIngress": [{
                        "IpProtocol": "tcp",
                        "FromPort": "22",
                        "ToPort": "22",
                        "CidrIp": "123.123.123.123/32",
                    }, {
                        "IpProtocol": "tcp",
                        "FromPort": "80",
                        "ToPort": "8000",
                        "SourceSecurityGroupId": {"Ref": "my-security-group"},
                    }]
                }
            }
        },
    }
    security_group_template_json = json.dumps(security_group_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "security_group_stack",
        template_body=security_group_template_json,
    )

    ec2_conn = boto.connect_ec2()
    security_groups = ec2_conn.get_all_security_groups()
    for group in security_groups:
        if group.name == "InstanceSecurityGroup":
            instance_group = group
        else:
            other_group = group

    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    ec2_instance.groups[0].id.should.equal(instance_group.id)
    instance_group.description.should.equal("My security group")
    rule1, rule2 = instance_group.rules
    int(rule1.to_port).should.equal(22)
    int(rule1.from_port).should.equal(22)
    rule1.grants[0].cidr_ip.should.equal("123.123.123.123/32")
    rule1.ip_protocol.should.equal('tcp')

    int(rule2.to_port).should.equal(8000)
    int(rule2.from_port).should.equal(80)
    rule2.ip_protocol.should.equal('tcp')
    rule2.grants[0].group_id.should.equal(other_group.id)


@mock_autoscaling()
@mock_elb()
@mock_cloudformation()
def test_autoscaling_group_with_elb():

    web_setup_template = {
        "AWSTemplateFormatVersion": "2010-09-09",

        "Resources": {
            "my-as-group": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "AvailabilityZones": ['us-east1'],
                    "LaunchConfigurationName": {"Ref": "my-launch-config"},
                    "MinSize": "2",
                    "MaxSize": "2",
                    "LoadBalancerNames": [{"Ref": "my-elb"}]
                },
            },

            "my-launch-config": {
                "Type": "AWS::AutoScaling::LaunchConfiguration",
                "Properties": {
                    "ImageId": "ami-1234abcd",
                    "UserData": "some user data",
                }
            },

            "my-elb": {
                "Type": "AWS::ElasticLoadBalancing::LoadBalancer",
                "Properties": {
                    "AvailabilityZones": ['us-east1'],
                    "Listeners": [{
                        "LoadBalancerPort": "80",
                        "InstancePort": "80",
                        "Protocol": "HTTP"
                    }],
                    "HealthCheck": {
                        "Target": "80",
                        "HealthyThreshold": "3",
                        "UnhealthyThreshold": "5",
                        "Interval": "30",
                        "Timeout": "5",
                    },
                },
            },
        }
    }

    web_setup_template_json = json.dumps(web_setup_template)

    conn = boto.connect_cloudformation()
    conn.create_stack(
        "web_stack",
        template_body=web_setup_template_json,
    )

    autoscale_conn = boto.connect_autoscale()
    autoscale_group = autoscale_conn.get_all_groups()[0]
    autoscale_group.launch_config_name.should.equal("my-launch-config")
    autoscale_group.load_balancers[0].should.equal('my-elb')

    # Confirm the Launch config was actually created
    autoscale_conn.get_all_launch_configurations().should.have.length_of(1)

    # Confirm the ELB was actually created
    elb_conn = boto.connect_elb()
    elb_conn.get_all_load_balancers().should.have.length_of(1)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    as_group_resource = [resource for resource in resources if resource.resource_type == 'AWS::AutoScaling::AutoScalingGroup'][0]
    as_group_resource.physical_resource_id.should.equal("my-as-group")

    launch_config_resource = [resource for resource in resources if resource.resource_type == 'AWS::AutoScaling::LaunchConfiguration'][0]
    launch_config_resource.physical_resource_id.should.equal("my-launch-config")

    elb_resource = [resource for resource in resources if resource.resource_type == 'AWS::ElasticLoadBalancing::LoadBalancer'][0]
    elb_resource.physical_resource_id.should.equal("my-elb")


@mock_ec2()
@mock_cloudformation()
def test_vpc_single_instance_in_subnet():

    template_json = json.dumps(vpc_single_instance_in_subnet.template)
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    vpc_conn = boto.connect_vpc()
    vpc = vpc_conn.get_all_vpcs()[0]
    vpc.cidr_block.should.equal("10.0.0.0/16")

    # Add this once we implement the endpoint
    # vpc_conn.get_all_internet_gateways().should.have.length_of(1)

    subnet = vpc_conn.get_all_subnets()[0]
    subnet.vpc_id.should.equal(vpc.id)

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    instance = reservation.instances[0]
    # Check that the EIP is attached the the EC2 instance
    eip = ec2_conn.get_all_addresses()[0]
    eip.domain.should.equal('vpc')
    eip.instance_id.should.equal(instance.id)

    security_group = ec2_conn.get_all_security_groups()[0]
    security_group.vpc_id.should.equal(vpc.id)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    vpc_resource = [resource for resource in resources if resource.resource_type == 'AWS::EC2::VPC'][0]
    vpc_resource.physical_resource_id.should.equal(vpc.id)

    subnet_resource = [resource for resource in resources if resource.resource_type == 'AWS::EC2::Subnet'][0]
    subnet_resource.physical_resource_id.should.equal(subnet.id)

    eip_resource = [resource for resource in resources if resource.resource_type == 'AWS::EC2::EIP'][0]
    eip_resource.physical_resource_id.should.equal(eip.allocation_id)


@mock_autoscaling()
@mock_iam()
@mock_cloudformation()
def test_iam_roles():
    iam_template = {
        "AWSTemplateFormatVersion": "2010-09-09",

        "Resources": {

            "my-launch-config": {
                "Properties": {
                    "IamInstanceProfile": {"Ref": "my-instance-profile"},
                    "ImageId": "ami-1234abcd",
                },
                "Type": "AWS::AutoScaling::LaunchConfiguration"
            },
            "my-instance-profile": {
                "Properties": {
                    "Path": "my-path",
                    "Roles": [{"Ref": "my-role"}],
                },
                "Type": "AWS::IAM::InstanceProfile"
            },
            "my-role": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Statement": [
                            {
                                "Action": [
                                    "sts:AssumeRole"
                                ],
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": [
                                        "ec2.amazonaws.com"
                                    ]
                                }
                            }
                        ]
                    },
                    "Path": "my-path",
                    "Policies": [
                        {
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": [
                                            "ec2:CreateTags",
                                            "ec2:DescribeInstances",
                                            "ec2:DescribeTags"
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "*"
                                        ]
                                    }
                                ],
                                "Version": "2012-10-17"
                            },
                            "PolicyName": "EC2_Tags"
                        },
                        {
                            "PolicyDocument": {
                                "Statement": [
                                    {
                                        "Action": [
                                            "sqs:*"
                                        ],
                                        "Effect": "Allow",
                                        "Resource": [
                                            "*"
                                        ]
                                    }
                                ],
                                "Version": "2012-10-17"
                            },
                            "PolicyName": "SQS"
                        },
                    ]
                },
                "Type": "AWS::IAM::Role"
            }
        }
    }

    iam_template_json = json.dumps(iam_template)
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=iam_template_json,
    )

    iam_conn = boto.connect_iam()

    role = iam_conn.get_role("my-role")
    role.role_name.should.equal("my-role")
    role.path.should.equal("my-path")

    instance_profile = iam_conn.get_instance_profile("my-instance-profile")
    instance_profile.instance_profile_name.should.equal("my-instance-profile")
    instance_profile.path.should.equal("my-path")
    instance_profile.role_id.should.equal(role.role_id)

    autoscale_conn = boto.connect_autoscale()
    launch_config = autoscale_conn.get_all_launch_configurations()[0]
    launch_config.instance_profile_name.should.equal("my-instance-profile")

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    instance_profile_resource = [resource for resource in resources if resource.resource_type == 'AWS::IAM::InstanceProfile'][0]
    instance_profile_resource.physical_resource_id.should.equal(instance_profile.instance_profile_name)

    role_resource = [resource for resource in resources if resource.resource_type == 'AWS::IAM::Role'][0]
    role_resource.physical_resource_id.should.equal(role.role_id)


@mock_ec2()
@mock_cloudformation()
def test_single_instance_with_ebs_volume():

    template_json = json.dumps(single_instance_with_ebs_volume.template)
    conn = boto.connect_cloudformation()
    conn.create_stack(
        "test_stack",
        template_body=template_json,
    )

    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.get_all_instances()[0]
    ec2_instance = reservation.instances[0]

    volume = ec2_conn.get_all_volumes()[0]
    volume.volume_state().should.equal('in-use')
    volume.attach_data.instance_id.should.equal(ec2_instance.id)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    ebs_volume = [resource for resource in resources if resource.resource_type == 'AWS::EC2::Volume'][0]
    ebs_volume.physical_resource_id.should.equal(volume.id)

########NEW FILE########
__FILENAME__ = test_server

########NEW FILE########
__FILENAME__ = test_stack_parsing
import json

from mock import patch
import sure  # noqa

from moto.cloudformation.models import FakeStack
from moto.cloudformation.parsing import resource_class_from_type
from moto.sqs.models import Queue

dummy_template = {
    "AWSTemplateFormatVersion": "2010-09-09",

    "Description": "Create a multi-az, load balanced, Auto Scaled sample web site. The Auto Scaling trigger is based on the CPU utilization of the web servers. The AMI is chosen based on the region in which the stack is run. This example creates a web service running across all availability zones in a region. The instances are load balanced with a simple health check. The web site is available on port 80, however, the instances can be configured to listen on any port (8888 by default). **WARNING** This template creates one or more Amazon EC2 instances. You will be billed for the AWS resources used if you create a stack from this template.",

    "Resources": {
        "WebServerGroup": {

            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": "my-queue",
                "VisibilityTimeout": 60,
            }
        },
    },
}

dummy_template_json = json.dumps(dummy_template)


def test_parse_stack_resources():
    stack = FakeStack(
        stack_id="test_id",
        name="test_stack",
        template=dummy_template_json,
    )

    stack.resource_map.should.have.length_of(1)
    stack.resource_map.keys()[0].should.equal('WebServerGroup')
    queue = stack.resource_map.values()[0]
    queue.should.be.a(Queue)
    queue.name.should.equal("my-queue")


@patch("moto.cloudformation.parsing.logger")
def test_missing_resource_logs(logger):
    resource_class_from_type("foobar")
    logger.warning.assert_called_with('No Moto CloudFormation support for %s', 'foobar')

########NEW FILE########
__FILENAME__ = test_decorator_calls
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2

'''
Test the different ways that the decorator can be used
'''


@mock_ec2
def test_basic_connect():
    boto.connect_ec2()


@mock_ec2
def test_basic_decorator():
    conn = boto.connect_ec2('the_key', 'the_secret')
    list(conn.get_all_instances()).should.equal([])


def test_context_manager():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)

    with mock_ec2():
        conn = boto.connect_ec2('the_key', 'the_secret')
        list(conn.get_all_instances()).should.equal([])

    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)


def test_decorator_start_and_stop():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)

    mock = mock_ec2()
    mock.start()
    conn = boto.connect_ec2('the_key', 'the_secret')
    list(conn.get_all_instances()).should.equal([])
    mock.stop()

    conn.get_all_instances.when.called_with().should.throw(EC2ResponseError)


@mock_ec2
def test_decorater_wrapped_gets_set():
    """
    Moto decorator's __wrapped__ should get set to the tests function
    """
    test_decorater_wrapped_gets_set.__wrapped__.__name__.should.equal('test_decorater_wrapped_gets_set')

########NEW FILE########
__FILENAME__ = test_instance_metadata
import requests

from moto import mock_ec2


@mock_ec2
def test_latest_meta_data():
    res = requests.get("http://169.254.169.254/latest/meta-data/")
    res.content.should.equal("iam")


@mock_ec2
def test_meta_data_iam():
    res = requests.get("http://169.254.169.254/latest/meta-data/iam")
    json_response = res.json()
    default_role = json_response['security-credentials']['default-role']
    default_role.should.contain('AccessKeyId')
    default_role.should.contain('SecretAccessKey')
    default_role.should.contain('Token')
    default_role.should.contain('Expiration')


@mock_ec2
def test_meta_data_security_credentials():
    res = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    res.content.should.equal("default-role")


@mock_ec2
def test_meta_data_default_role():
    res = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/default-role")
    json_response = res.json()
    json_response.should.contain('AccessKeyId')
    json_response.should.contain('SecretAccessKey')
    json_response.should.contain('Token')
    json_response.should.contain('Expiration')

########NEW FILE########
__FILENAME__ = test_nested
import unittest

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from boto.ec2 import EC2Connection

from moto import mock_sqs, mock_ec2


class TestNestedDecorators(unittest.TestCase):

    @mock_sqs
    def setup_sqs_queue(self):
        conn = SQSConnection()
        q = conn.create_queue('some-queue')

        m = Message()
        m.set_body('This is my first message.')
        q.write(m)

        self.assertEqual(q.count(), 1)

    @mock_ec2
    def test_nested(self):
        self.setup_sqs_queue()

        conn = EC2Connection()
        conn.run_instances('ami-123456')
########NEW FILE########
__FILENAME__ = test_server
from mock import patch
import sure  # noqa

from moto.server import main, create_backend_app, DomainDispatcherApplication


def test_wrong_arguments():
    try:
        main(["name", "test1", "test2", "test3"])
        assert False, ("main() when called with the incorrect number of args"
                       " should raise a system exit")
    except SystemExit:
        pass


@patch('moto.server.run_simple')
def test_right_arguments(run_simple):
    main(["s3"])
    func_call = run_simple.call_args[0]
    func_call[0].should.equal("0.0.0.0")
    func_call[1].should.equal(5000)


@patch('moto.server.run_simple')
def test_port_argument(run_simple):
    main(["s3", "--port", "8080"])
    func_call = run_simple.call_args[0]
    func_call[0].should.equal("0.0.0.0")
    func_call[1].should.equal(8080)


def test_domain_dispatched():
    dispatcher = DomainDispatcherApplication(create_backend_app)
    backend_app = dispatcher.get_application("email.us-east1.amazonaws.com")
    backend_app.view_functions.keys()[0].should.equal('EmailResponse.dispatch')


def test_domain_without_matches():
    dispatcher = DomainDispatcherApplication(create_backend_app)
    dispatcher.get_application.when.called_with("not-matching-anything.com").should.throw(RuntimeError)


def test_domain_dispatched_with_service():
    # If we pass a particular service, always return that.
    dispatcher = DomainDispatcherApplication(create_backend_app, service="s3")
    backend_app = dispatcher.get_application("s3.us-east1.amazonaws.com")
    backend_app.view_functions.keys()[0].should.equal('ResponseObject.key_response')

########NEW FILE########
__FILENAME__ = test_url_mapping
import sure  # noqa

from moto.core.utils import convert_regex_to_flask_path


def test_flask_path_converting_simple():
    convert_regex_to_flask_path("/").should.equal("/")
    convert_regex_to_flask_path("/$").should.equal("/")

    convert_regex_to_flask_path("/foo").should.equal("/foo")

    convert_regex_to_flask_path("/foo/bar/").should.equal("/foo/bar/")


def test_flask_path_converting_regex():
    convert_regex_to_flask_path("/(?P<key_name>[a-zA-Z0-9\-_]+)").should.equal('/<regex("[a-zA-Z0-9\-_]+"):key_name>')

    convert_regex_to_flask_path("(?P<account_id>\d+)/(?P<queue_name>.*)$").should.equal(
        '<regex("\d+"):account_id>/<regex(".*"):queue_name>'
    )

########NEW FILE########
__FILENAME__ = test_dynamodb
import boto
import sure  # noqa
import requests

from moto import mock_dynamodb
from moto.dynamodb import dynamodb_backend

from boto.exception import DynamoDBResponseError


@mock_dynamodb
def test_list_tables():
    name = 'TestTable'
    dynamodb_backend.create_table(name, hash_key_attr="name", hash_key_type="S")
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    assert conn.list_tables() == ['TestTable']


@mock_dynamodb
def test_list_tables_layer_1():
    dynamodb_backend.create_table("test_1", hash_key_attr="name", hash_key_type="S")
    dynamodb_backend.create_table("test_2", hash_key_attr="name", hash_key_type="S")
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    res = conn.layer1.list_tables(limit=1)
    expected = {"TableNames": ["test_1"], "LastEvaluatedTableName": "test_1"}
    res.should.equal(expected)

    res = conn.layer1.list_tables(limit=1, start_table="test_1")
    expected = {"TableNames": ["test_2"]}
    res.should.equal(expected)


@mock_dynamodb
def test_describe_missing_table():
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    conn.describe_table.when.called_with('messages').should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_sts_handler():
    res = requests.post("https://sts.amazonaws.com/", data={"GetSessionToken": ""})
    res.ok.should.be.ok
    res.text.should.contain("SecretAccessKey")


@mock_dynamodb
def test_dynamodb_with_connect_to_region():
    # this will work if connected with boto.connect_dynamodb()
    dynamodb = boto.dynamodb.connect_to_region('us-west-2')

    schema = dynamodb.create_schema('column1', str(), 'column2', int())
    dynamodb.create_table('table1', schema, 200, 200)

########NEW FILE########
__FILENAME__ = test_dynamodb_table_without_range_key
import boto
import sure  # noqa
from freezegun import freeze_time

from moto import mock_dynamodb

from boto.dynamodb import condition
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError
from boto.exception import DynamoDBResponseError


def create_table(conn):
    message_table_schema = conn.create_schema(
        hash_key_name='forum_name',
        hash_key_proto_value=str,
    )

    table = conn.create_table(
        name='messages',
        schema=message_table_schema,
        read_units=10,
        write_units=10
    )
    return table


@freeze_time("2012-01-14")
@mock_dynamodb
def test_create_table():
    conn = boto.connect_dynamodb()
    create_table(conn)

    expected = {
        'Table': {
            'CreationDateTime': 1326499200.0,
            'ItemCount': 0,
            'KeySchema': {
                'HashKeyElement': {
                    'AttributeName': 'forum_name',
                    'AttributeType': 'S'
                },
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            },
            'TableName': 'messages',
            'TableSizeBytes': 0,
            'TableStatus': 'ACTIVE'
        }
    }
    conn.describe_table('messages').should.equal(expected)


@mock_dynamodb
def test_delete_table():
    conn = boto.connect_dynamodb()
    create_table(conn)
    conn.list_tables().should.have.length_of(1)

    conn.layer1.delete_table('messages')
    conn.list_tables().should.have.length_of(0)

    conn.layer1.delete_table.when.called_with('messages').should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_update_table_throughput():
    conn = boto.connect_dynamodb()
    table = create_table(conn)
    table.read_units.should.equal(10)
    table.write_units.should.equal(10)

    table.update_throughput(5, 6)
    table.refresh()

    table.read_units.should.equal(5)
    table.write_units.should.equal(6)


@mock_dynamodb
def test_item_add_and_describe_and_update():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        attrs=item_data,
    )
    item.put()

    returned_item = table.get_item(
        hash_key='LOLCat Forum',
        attributes_to_get=['Body', 'SentBy']
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
    })

    item['SentBy'] = 'User B'
    item.put()

    returned_item = table.get_item(
        hash_key='LOLCat Forum',
        attributes_to_get=['Body', 'SentBy']
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
    })


@mock_dynamodb
def test_item_put_without_table():
    conn = boto.connect_dynamodb()

    conn.layer1.put_item.when.called_with(
        table_name='undeclared-table',
        item=dict(
            hash_key='LOLCat Forum',
        ),
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_get_missing_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    table.get_item.when.called_with(
        hash_key='tester',
    ).should.throw(DynamoDBKeyNotFoundError)


@mock_dynamodb
def test_get_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.get_item.when.called_with(
        table_name='undeclared-table',
        key={
            'HashKeyElement': {'S': 'tester'},
        },
    ).should.throw(DynamoDBKeyNotFoundError)


@mock_dynamodb
def test_delete_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        attrs=item_data,
    )
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete()
    response.should.equal({u'Attributes': [], u'ConsumedCapacityUnits': 0.5})
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_delete_item_with_attribute_response():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        attrs=item_data,
    )
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete(return_values='ALL_OLD')
    response.should.equal({
        u'Attributes': {
            u'Body': u'http://url_to_lolcat.gif',
            u'forum_name': u'LOLCat Forum',
            u'ReceivedTime': u'12/9/2011 11:36:03 PM',
            u'SentBy': u'User A',
        },
        u'ConsumedCapacityUnits': 0.5
    })
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_delete_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.delete_item.when.called_with(
        table_name='undeclared-table',
        key={
            'HashKeyElement': {'S': 'tester'},
        },
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_query():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        attrs=item_data,
    )
    item.put()

    results = table.query(hash_key='the-key')
    results.response['Items'].should.have.length_of(1)


@mock_dynamodb
def test_query_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.query.when.called_with(
        table_name='undeclared-table',
        hash_key_value={'S': 'the-key'},
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_scan():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key2',
        attrs=item_data,
    )
    item.put()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = table.new_item(
        hash_key='the-key3',
        attrs=item_data,
    )
    item.put()

    results = table.scan()
    results.response['Items'].should.have.length_of(3)

    results = table.scan(scan_filter={'SentBy': condition.EQ('User B')})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Body': condition.BEGINS_WITH('http')})
    results.response['Items'].should.have.length_of(3)

    results = table.scan(scan_filter={'Ids': condition.CONTAINS(2)})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Ids': condition.NOT_NULL()})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Ids': condition.NULL()})
    results.response['Items'].should.have.length_of(2)

    results = table.scan(scan_filter={'PK': condition.BETWEEN(8, 9)})
    results.response['Items'].should.have.length_of(0)

    results = table.scan(scan_filter={'PK': condition.BETWEEN(5, 8)})
    results.response['Items'].should.have.length_of(1)


@mock_dynamodb
def test_scan_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.scan.when.called_with(
        table_name='undeclared-table',
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{
                    "S": "User B"}
                ],
                "ComparisonOperator": "EQ"
            }
        },
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_write_batch():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    batch_list = conn.new_batch_write_list()

    items = []
    items.append(table.new_item(
        hash_key='the-key',
        attrs={
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        },
    ))

    items.append(table.new_item(
        hash_key='the-key2',
        attrs={
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User B',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
            'Ids': set([1, 2, 3]),
            'PK': 7,
        },
    ))

    batch_list.add_batch(table, puts=items)
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(2)

    batch_list = conn.new_batch_write_list()
    batch_list.add_batch(table, deletes=[('the-key')])
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(1)


@mock_dynamodb
def test_batch_read():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key1',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key2',
        attrs=item_data,
    )
    item.put()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = table.new_item(
        hash_key='another-key',
        attrs=item_data,
    )
    item.put()

    items = table.batch_get_item([('the-key1'), ('another-key')])
    # Iterate through so that batch_item gets called
    count = len([x for x in items])
    count.should.have.equal(2)

########NEW FILE########
__FILENAME__ = test_dynamodb_table_with_range_key
import boto
import sure  # noqa
from freezegun import freeze_time

from moto import mock_dynamodb

from boto.dynamodb import condition
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError, DynamoDBValidationError
from boto.exception import DynamoDBResponseError


def create_table(conn):
    message_table_schema = conn.create_schema(
        hash_key_name='forum_name',
        hash_key_proto_value=str,
        range_key_name='subject',
        range_key_proto_value=str
    )

    table = conn.create_table(
        name='messages',
        schema=message_table_schema,
        read_units=10,
        write_units=10
    )
    return table


@freeze_time("2012-01-14")
@mock_dynamodb
def test_create_table():
    conn = boto.connect_dynamodb()
    create_table(conn)

    expected = {
        'Table': {
            'CreationDateTime': 1326499200.0,
            'ItemCount': 0,
            'KeySchema': {
                'HashKeyElement': {
                    'AttributeName': 'forum_name',
                    'AttributeType': 'S'
                },
                'RangeKeyElement': {
                    'AttributeName': 'subject',
                    'AttributeType': 'S'
                }
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            },
            'TableName': 'messages',
            'TableSizeBytes': 0,
            'TableStatus': 'ACTIVE'
        }
    }
    conn.describe_table('messages').should.equal(expected)


@mock_dynamodb
def test_delete_table():
    conn = boto.connect_dynamodb()
    create_table(conn)
    conn.list_tables().should.have.length_of(1)

    conn.layer1.delete_table('messages')
    conn.list_tables().should.have.length_of(0)

    conn.layer1.delete_table.when.called_with('messages').should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_update_table_throughput():
    conn = boto.connect_dynamodb()
    table = create_table(conn)
    table.read_units.should.equal(10)
    table.write_units.should.equal(10)

    table.update_throughput(5, 6)
    table.refresh()

    table.read_units.should.equal(5)
    table.write_units.should.equal(6)


@mock_dynamodb
def test_item_add_and_describe_and_update():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attrs=item_data,
    )
    item.put()

    table.has_item("LOLCat Forum", "Check this out!").should.equal(True)

    returned_item = table.get_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attributes_to_get=['Body', 'SentBy']
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
    })

    item['SentBy'] = 'User B'
    item.put()

    returned_item = table.get_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attributes_to_get=['Body', 'SentBy']
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
    })


@mock_dynamodb
def test_item_put_without_table():
    conn = boto.connect_dynamodb()

    conn.layer1.put_item.when.called_with(
        table_name='undeclared-table',
        item=dict(
            hash_key='LOLCat Forum',
            range_key='Check this out!',
        ),
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_get_missing_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    table.get_item.when.called_with(
        hash_key='tester',
        range_key='other',
    ).should.throw(DynamoDBKeyNotFoundError)
    table.has_item("foobar", "more").should.equal(False)


@mock_dynamodb
def test_get_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.get_item.when.called_with(
        table_name='undeclared-table',
        key={
            'HashKeyElement': {'S': 'tester'},
            'RangeKeyElement': {'S': 'test-range'},
        },
    ).should.throw(DynamoDBKeyNotFoundError)


@mock_dynamodb
def test_get_item_without_range_key():
    conn = boto.connect_dynamodb()
    message_table_schema = conn.create_schema(
        hash_key_name="test_hash",
        hash_key_proto_value=int,
        range_key_name="test_range",
        range_key_proto_value=int,
    )
    table = conn.create_table(
        name='messages',
        schema=message_table_schema,
        read_units=10,
        write_units=10
    )

    hash_key = 3241526475
    range_key = 1234567890987
    new_item = table.new_item(hash_key=hash_key, range_key=range_key)
    new_item.put()

    table.get_item.when.called_with(hash_key=hash_key).should.throw(DynamoDBValidationError)


@mock_dynamodb
def test_delete_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attrs=item_data,
    )
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete()
    response.should.equal({u'Attributes': [], u'ConsumedCapacityUnits': 0.5})
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_delete_item_with_attribute_response():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='LOLCat Forum',
        range_key='Check this out!',
        attrs=item_data,
    )
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete(return_values='ALL_OLD')
    response.should.equal({
        u'Attributes': {
            u'Body': u'http://url_to_lolcat.gif',
            u'forum_name': u'LOLCat Forum',
            u'ReceivedTime': u'12/9/2011 11:36:03 PM',
            u'SentBy': u'User A',
            u'subject': u'Check this out!'
        },
        u'ConsumedCapacityUnits': 0.5
    })
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_delete_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.delete_item.when.called_with(
        table_name='undeclared-table',
        key={
            'HashKeyElement': {'S': 'tester'},
            'RangeKeyElement': {'S': 'test-range'},
        },
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_query():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='456',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='789',
        attrs=item_data,
    )
    item.put()

    results = table.query(hash_key='the-key', range_key_condition=condition.GT('1'))
    results.response['Items'].should.have.length_of(3)

    results = table.query(hash_key='the-key', range_key_condition=condition.GT('234'))
    results.response['Items'].should.have.length_of(2)

    results = table.query(hash_key='the-key', range_key_condition=condition.GT('9999'))
    results.response['Items'].should.have.length_of(0)

    results = table.query(hash_key='the-key', range_key_condition=condition.CONTAINS('12'))
    results.response['Items'].should.have.length_of(1)

    results = table.query(hash_key='the-key', range_key_condition=condition.BEGINS_WITH('7'))
    results.response['Items'].should.have.length_of(1)

    results = table.query(hash_key='the-key', range_key_condition=condition.BETWEEN('567', '890'))
    results.response['Items'].should.have.length_of(1)


@mock_dynamodb
def test_query_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.query.when.called_with(
        table_name='undeclared-table',
        hash_key_value={'S': 'the-key'},
        range_key_conditions={
            "AttributeValueList": [{
                "S": "User B"
            }],
            "ComparisonOperator": "EQ",
        },
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_scan():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='456',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs=item_data,
    )
    item.put()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='789',
        attrs=item_data,
    )
    item.put()

    results = table.scan()
    results.response['Items'].should.have.length_of(3)

    results = table.scan(scan_filter={'SentBy': condition.EQ('User B')})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Body': condition.BEGINS_WITH('http')})
    results.response['Items'].should.have.length_of(3)

    results = table.scan(scan_filter={'Ids': condition.CONTAINS(2)})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Ids': condition.NOT_NULL()})
    results.response['Items'].should.have.length_of(1)

    results = table.scan(scan_filter={'Ids': condition.NULL()})
    results.response['Items'].should.have.length_of(2)

    results = table.scan(scan_filter={'PK': condition.BETWEEN(8, 9)})
    results.response['Items'].should.have.length_of(0)

    results = table.scan(scan_filter={'PK': condition.BETWEEN(5, 8)})
    results.response['Items'].should.have.length_of(1)


@mock_dynamodb
def test_scan_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.scan.when.called_with(
        table_name='undeclared-table',
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{
                    "S": "User B"}
                ],
                "ComparisonOperator": "EQ"
            }
        },
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb
def test_write_batch():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    batch_list = conn.new_batch_write_list()

    items = []
    items.append(table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs={
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        },
    ))

    items.append(table.new_item(
        hash_key='the-key',
        range_key='789',
        attrs={
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User B',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
            'Ids': set([1, 2, 3]),
            'PK': 7,
        },
    ))

    batch_list.add_batch(table, puts=items)
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(2)

    batch_list = conn.new_batch_write_list()
    batch_list.add_batch(table, deletes=[('the-key', '789')])
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(1)


@mock_dynamodb
def test_batch_read():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item = table.new_item(
        hash_key='the-key',
        range_key='456',
        attrs=item_data,
    )
    item.put()

    item = table.new_item(
        hash_key='the-key',
        range_key='123',
        attrs=item_data,
    )
    item.put()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = table.new_item(
        hash_key='another-key',
        range_key='789',
        attrs=item_data,
    )
    item.put()

    items = table.batch_get_item([('the-key', '123'), ('another-key', '789')])
    # Iterate through so that batch_item gets called
    count = len([x for x in items])
    count.should.equal(2)

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_table_list():
    backend = server.create_backend_app("dynamodb")
    test_client = backend.test_client()

    res = test_client.get('/')
    res.status_code.should.equal(404)

    headers = {'X-Amz-Target': 'TestTable.ListTables'}
    res = test_client.get('/', headers=headers)
    res.data.should.contain('TableNames')

########NEW FILE########
__FILENAME__ = test_dynamodb
import boto
import sure  # noqa
import requests
from moto import mock_dynamodb2
from moto.dynamodb2 import dynamodb_backend2
from boto.exception import JSONResponseError
from tests.helpers import requires_boto_gte
try:
    import boto.dynamodb2
except ImportError:
    print "This boto version is not supported"

@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_tables():
    name = 'TestTable'    
    #{'schema': }    
    dynamodb_backend2.create_table(name,schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'forum_name'}, 
        {u'KeyType': u'RANGE', u'AttributeName': u'subject'}
    ])
    conn =  boto.dynamodb2.connect_to_region(
            'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    assert conn.list_tables()["TableNames"] == [name]


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_list_tables_layer_1():
    dynamodb_backend2.create_table("test_1",schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])
    dynamodb_backend2.create_table("test_2",schema=[
        {u'KeyType': u'HASH', u'AttributeName': u'name'}
    ])
    conn =  boto.dynamodb2.connect_to_region(
        'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    
    res = conn.list_tables(limit=1)
    expected = {"TableNames": ["test_1"], "LastEvaluatedTableName": "test_1"}
    res.should.equal(expected)

    res = conn.list_tables(limit=1, exclusive_start_table_name="test_1")
    expected = {"TableNames": ["test_2"]}
    res.should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_describe_missing_table():
    conn =  boto.dynamodb2.connect_to_region(
        'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    conn.describe_table.when.called_with('messages').should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_sts_handler():
    res = requests.post("https://sts.amazonaws.com/", data={"GetSessionToken": ""})
    res.ok.should.be.ok
    res.text.should.contain("SecretAccessKey")

########NEW FILE########
__FILENAME__ = test_dynamodb_table_without_range_key
import boto
import sure  # noqa
from freezegun import freeze_time
from boto.exception import JSONResponseError
from moto import mock_dynamodb2
from tests.helpers import requires_boto_gte
try:
    from boto.dynamodb2.fields import HashKey
    from boto.dynamodb2.fields import RangeKey
    from boto.dynamodb2.table import Table
    from boto.dynamodb2.table import Item
except ImportError:
    print "This boto version is not supported"
    
def create_table():
    table = Table.create('messages', schema=[
        HashKey('forum_name')
    ], throughput={
        'read': 10,
        'write': 10,
    })
    return table



@requires_boto_gte("2.9")
@mock_dynamodb2
@freeze_time("2012-01-14")
def test_create_table():
    table = create_table()
    expected = {
        'Table': {
            'AttributeDefinitions': [
                {'AttributeName': 'forum_name', 'AttributeType': 'S'}    
            ], 
            'ProvisionedThroughput': {
                'NumberOfDecreasesToday': 0, 'WriteCapacityUnits': 10, 'ReadCapacityUnits': 10
                }, 
            'TableSizeBytes': 0, 
            'TableName': 'messages', 
            'TableStatus': 'ACTIVE', 
            'KeySchema': [
                {'KeyType': 'HASH', 'AttributeName': 'forum_name'} 
            ], 
            'ItemCount': 0, 'CreationDateTime': 1326499200.0
        }
    }
    conn =  boto.dynamodb2.connect_to_region(
            'us-west-2',
        aws_access_key_id="ak",
        aws_secret_access_key="sk")
    
    conn.describe_table('messages').should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_table():
    create_table()
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    conn.list_tables()["TableNames"].should.have.length_of(1)

    conn.delete_table('messages')
    conn.list_tables()["TableNames"].should.have.length_of(0)

    conn.delete_table.when.called_with('messages').should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_update_table_throughput():
    table = create_table()
    table.throughput["read"].should.equal(10)
    table.throughput["write"].should.equal(10)    

    table.update(throughput={
        'read': 5,
        'write': 6,
     })


    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(6)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_add_and_describe_and_update():
    table = create_table()
    
    data={
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
     }
    
    table.put_item(data = data)
    returned_item = table.get_item(forum_name="LOLCat Forum")
    returned_item.should_not.be.none
    
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
    })

    returned_item['SentBy'] = 'User B'
    returned_item.save(overwrite=True)

    returned_item = table.get_item(
          forum_name='LOLCat Forum'
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
    })


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_put_without_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.put_item.when.called_with(
        table_name='undeclared-table',
        item={
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        }
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_missing_item():
    table = create_table()

    table.get_item.when.called_with(test_hash=3241526475).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_item_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.get_item.when.called_with(
        table_name='undeclared-table',
        key={"forum_name": {"S": "LOLCat Forum"}},
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item():
    table = create_table()

    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)
    item.save()
    table.count().should.equal(1)

    response = item.delete()
    
    response.should.equal(True)

    table.count().should.equal(0)

    item.delete.when.called_with().should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.delete_item.when.called_with(
        table_name='undeclared-table',
        key={"forum_name": {"S": "LOLCat Forum"}},
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query():
    table = create_table()

    item_data = {
        'forum_name': 'the-key',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)     
    item.save(overwrite = True)
    table.count().should.equal(1)
    table = Table("messages")
    
    results = table.query(forum_name__eq='the-key')
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.query.when.called_with(
        table_name='undeclared-table',
         key_conditions= {"forum_name": {"ComparisonOperator": "EQ", "AttributeValueList": [{"S": "the-key"}]}}
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan():
    table = create_table()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item_data['forum_name'] = 'the-key'
    
    item = Item(table,item_data)     
    item.save()    

    item['forum_name'] = 'the-key2'
    item.save(overwrite=True)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item_data['forum_name'] = 'the-key3'
    item = Item(table,item_data)     
    item.save() 

    results = table.scan()
    sum(1 for _ in results).should.equal(3)

    results = table.scan(SentBy__eq='User B')
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Body__beginswith='http')
    sum(1 for _ in results).should.equal(3)

    results = table.scan(Ids__null=False)
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Ids__null=True)
    sum(1 for _ in results).should.equal(2)

    results = table.scan(PK__between=[8, 9])
    sum(1 for _ in results).should.equal(0)

    results = table.scan(PK__between=[5, 8])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    conn.scan.when.called_with(
        table_name='undeclared-table',
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{
                    "S": "User B"}
                ],
                "ComparisonOperator": "EQ"
            }
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_write_batch():
    table = create_table()

    with table.batch_write() as batch:
        batch.put_item(data={
            'forum_name': 'the-key',
            'subject': '123',
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        })  
        batch.put_item(data={
            'forum_name': 'the-key2',
            'subject': '789',
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User B',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        }) 

    table.count().should.equal(2)
    with table.batch_write() as batch:
        batch.delete_item(
            forum_name='the-key',
            subject='789'
        )

    table.count().should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_batch_read():
    table = create_table()

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item_data['forum_name'] = 'the-key1'
    item = Item(table,item_data)     
    item.save()  

    item = Item(table,item_data)
    item_data['forum_name'] = 'the-key2'
    item.save(overwrite = True)

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = Item(table,item_data) 
    item_data['forum_name'] = 'another-key'
    item.save(overwrite = True)
    
    results = table.batch_get(keys=[
                {'forum_name': 'the-key1'},
                {'forum_name': 'another-key'}])

    # Iterate through so that batch_item gets called
    count = len([x for x in results])
    count.should.equal(2)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_key_fields():
    table = create_table()
    kf = table.get_key_fields()
    kf[0].should.equal('forum_name')


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_special_item():
    table = Table.create('messages', schema=[
        HashKey('date-joined')
    ], throughput={
        'read': 10,
        'write': 10,
    })
    
    data={
        'date-joined': 127549192,
        'SentBy': 'User A',
    }
    table.put_item(data = data)
    returned_item = table.get_item(**{'date-joined': 127549192})
    dict(returned_item).should.equal(data)
    

########NEW FILE########
__FILENAME__ = test_dynamodb_table_with_range_key
import boto
import sure  # noqa
from freezegun import freeze_time
from moto import mock_dynamodb2
from boto.exception import JSONResponseError
from tests.helpers import requires_boto_gte
try:
    from boto.dynamodb2.fields import HashKey
    from boto.dynamodb2.fields import RangeKey
    from boto.dynamodb2.table import Table
    from boto.dynamodb2.table import Item
    from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError
    from boto.dynamodb2.exceptions import ValidationException
    from boto.dynamodb2.exceptions import ConditionalCheckFailedException
except ImportError:
    print "This boto version is not supported"
    
def create_table():
    table = Table.create('messages', schema=[
        HashKey('forum_name'),
        RangeKey('subject'),
    ], throughput={
        'read': 10,
        'write': 10,
    })
    return table

def iterate_results(res):
    for i in res:
        print i



@requires_boto_gte("2.9")
@mock_dynamodb2
@freeze_time("2012-01-14")
def test_create_table():
    table = create_table()
    expected = {
        'Table': {
            'AttributeDefinitions': [
                {'AttributeName': 'forum_name', 'AttributeType': 'S'}, 
                {'AttributeName': 'subject', 'AttributeType': 'S'}
            ], 
            'ProvisionedThroughput': {
                'NumberOfDecreasesToday': 0, 'WriteCapacityUnits': 10, 'ReadCapacityUnits': 10
                }, 
            'TableSizeBytes': 0, 
            'TableName': 'messages', 
            'TableStatus': 'ACTIVE', 
            'KeySchema': [
                {'KeyType': 'HASH', 'AttributeName': 'forum_name'}, 
                {'KeyType': 'RANGE', 'AttributeName': 'subject'}
            ], 
            'ItemCount': 0, 'CreationDateTime': 1326499200.0
        }
    }
    table.describe().should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    table = create_table()
    conn.list_tables()["TableNames"].should.have.length_of(1)

    table.delete()
    conn.list_tables()["TableNames"].should.have.length_of(0)
    conn.delete_table.when.called_with('messages').should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_update_table_throughput():
    table = create_table()
    table.throughput["read"].should.equal(10)
    table.throughput["write"].should.equal(10)    
    table.update(throughput={
        'read': 5,
        'write': 15,
     })
    
    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(15)

    table.update(throughput={
        'read': 5,
        'write': 6,
     })
    
    table.describe()

    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(6)
    
    
@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_add_and_describe_and_update():
    table = create_table()
    ok = table.put_item(data={
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
     })
    ok.should.equal(True)
    
    table.get_item(forum_name="LOLCat Forum",subject='Check this out!').should_not.be.none

    returned_item = table.get_item(
        forum_name='LOLCat Forum',
        subject='Check this out!'
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    })
    
    returned_item['SentBy'] = 'User B'
    returned_item.save(overwrite=True)

    returned_item = table.get_item(
        forum_name='LOLCat Forum',
        subject='Check this out!'
    )
    dict(returned_item).should.equal({
        'forum_name': 'LOLCat Forum',
        'subject': 'Check this out!',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    })
    
    
@requires_boto_gte("2.9")
@mock_dynamodb2
def test_item_put_without_table():

    table = Table('undeclared-table')
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)   
    item.save.when.called_with().should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_missing_item():

    table = create_table()

    table.get_item.when.called_with(
        hash_key='tester',
        range_key='other',
    ).should.throw(ValidationException)
    

@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_item_with_undeclared_table():
    table = Table('undeclared-table')
    table.get_item.when.called_with(test_hash=3241526475).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_item_without_range_key():
    table = Table.create('messages', schema=[
        HashKey('test_hash'),
        RangeKey('test_range'),
    ], throughput={
        'read': 10,
        'write': 10,
    })
    
    hash_key = 3241526475
    range_key = 1234567890987
    table.put_item( data = {'test_hash':hash_key, 'test_range':range_key})
    table.get_item.when.called_with(test_hash=hash_key).should.throw(ValidationException)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item():
    table = create_table()
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)
    item['subject'] = 'Check this out!'        
    item.save()
    table.count().should.equal(1)

    response = item.delete()
    response.should.equal(True)
    
    table.count().should.equal(0)
    item.delete.when.called_with().should.throw(ConditionalCheckFailedException)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_delete_item_with_undeclared_table():
    conn = boto.connect_dynamodb()
    table = Table("undeclared-table")
    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item =Item(table,item_data)
    item.delete.when.called_with().should.throw(JSONResponseError)
    

@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query():

    table = create_table()

    item_data = {
        'forum_name': 'LOLCat Forum',
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'subject': 'Check this out!' 
    }
    item =Item(table,item_data)     
    item.save(overwrite=True)
    
    item['forum_name'] = 'the-key'
    item['subject'] = '456'
    item.save(overwrite=True)

    item['forum_name'] = 'the-key'
    item['subject'] = '123'
    item.save(overwrite=True)
    
    item['forum_name'] = 'the-key'
    item['subject'] = '789'
    item.save(overwrite=True)

    table.count().should.equal(4)

    results = table.query(forum_name__eq='the-key', subject__gt='1',consistent=True)
    expected = ["123", "456", "789"]
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[index])

    results = table.query(forum_name__eq="the-key", subject__gt='1', reverse=True)
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[len(expected)-1-index])

    results = table.query(forum_name__eq='the-key', subject__gt='1',consistent=True)
    sum(1 for _ in results).should.equal(3)

    results = table.query(forum_name__eq='the-key', subject__gt='234',consistent=True)
    sum(1 for _ in results).should.equal(2)
    
    results = table.query(forum_name__eq='the-key', subject__gt='9999')
    sum(1 for _ in results).should.equal(0)
    
    results = table.query(forum_name__eq='the-key', subject__beginswith='12')
    sum(1 for _ in results).should.equal(1)
    
    results = table.query(forum_name__eq='the-key', subject__beginswith='7')
    sum(1 for _ in results).should.equal(1)

    results = table.query(forum_name__eq='the-key', subject__between=['567', '890'])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_query_with_undeclared_table():
    table = Table('undeclared')
    results = table.query(
        forum_name__eq='Amazon DynamoDB',
        subject__beginswith='DynamoDB',
        limit=1
    )
    iterate_results.when.called_with(results).should.throw(JSONResponseError)

    
@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan():
    table = create_table()    
    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '456'
    
    item = Item(table,item_data)     
    item.save()    

    item['forum_name'] = 'the-key'
    item['subject'] = '123'
    item.save()
   
    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:09 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    
    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '789'
    
    item = Item(table,item_data)     
    item.save()    

    results = table.scan()
    sum(1 for _ in results).should.equal(3)

    results = table.scan(SentBy__eq='User B')
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Body__beginswith='http')
    sum(1 for _ in results).should.equal(3)

    results = table.scan(Ids__null=False)
    sum(1 for _ in results).should.equal(1)
    
    results = table.scan(Ids__null=True)
    sum(1 for _ in results).should.equal(2)
    
    results = table.scan(PK__between=[8, 9])
    sum(1 for _ in results).should.equal(0)

    results = table.scan(PK__between=[5, 8])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_scan_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    conn.scan.when.called_with(
        table_name='undeclared-table',
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{
                    "S": "User B"}
                ],
                "ComparisonOperator": "EQ"
            }
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_write_batch():
    table = create_table()
    with table.batch_write() as batch:
        batch.put_item(data={
            'forum_name': 'the-key',
            'subject': '123',
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        })  
        batch.put_item(data={
            'forum_name': 'the-key',
            'subject': '789',
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User B',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        }) 
        
    table.count().should.equal(2)
    with table.batch_write() as batch:
        batch.delete_item(
            forum_name='the-key',
            subject='789'
        )

    table.count().should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2
def test_batch_read():
    table = create_table()
    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User A',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
    }
    
    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '456'
    
    item = Item(table,item_data)     
    item.save()    

    item = Item(table,item_data) 
    item_data['forum_name'] = 'the-key'
    item_data['subject'] = '123'
    item.save() 

    item_data = {
        'Body': 'http://url_to_lolcat.gif',
        'SentBy': 'User B',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'Ids': set([1, 2, 3]),
        'PK': 7,
    }
    item = Item(table,item_data) 
    item_data['forum_name'] = 'another-key'
    item_data['subject'] = '789'
    item.save() 
    results = table.batch_get(keys=[
                {'forum_name': 'the-key', 'subject': '123'},
                {'forum_name': 'another-key', 'subject': '789'}])

    # Iterate through so that batch_item gets called
    count = len([x for x in results])
    count.should.equal(2)

@requires_boto_gte("2.9")
@mock_dynamodb2
def test_get_key_fields():
    table = create_table()
    kf = table.get_key_fields()
    kf.should.equal(['forum_name','subject'])

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_table_list():
    backend = server.create_backend_app("dynamodb2")
    test_client = backend.test_client()
    res = test_client.get('/')
    res.status_code.should.equal(404)

    headers = {'X-Amz-Target': 'TestTable.ListTables'}
    res = test_client.get('/', headers=headers)
    res.data.should.contain('TableNames')

########NEW FILE########
__FILENAME__ = test_amazon_dev_pay
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_amazon_dev_pay():
    pass

########NEW FILE########
__FILENAME__ = test_amis
import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_ami_create_and_delete():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    image = conn.create_image(instance.id, "test-ami", "this is a test ami")

    all_images = conn.get_all_images()
    all_images[0].id.should.equal(image)

    success = conn.deregister_image(image)
    success.should.be.true

    success = conn.deregister_image.when.called_with(image).should.throw(EC2ResponseError)


@mock_ec2
def test_ami_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_all_images()[0]

    image.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the DHCP options
    image = conn.get_all_images()[0]
    image.tags.should.have.length_of(1)
    image.tags["a key"].should.equal("some value")


@mock_ec2
def test_ami_create_from_missing_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    args = ["i-abcdefg", "test-ami", "this is a test ami"]
    conn.create_image.when.called_with(*args).should.throw(EC2ResponseError)


@mock_ec2
def test_ami_pulls_attributes_from_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.kernel_id.should.equal('test-kernel')


@mock_ec2
def test_getting_missing_ami():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_image.when.called_with('ami-missing').should.throw(EC2ResponseError)

########NEW FILE########
__FILENAME__ = test_availability_zones_and_regions
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_describe_regions():
    conn = boto.connect_ec2('the_key', 'the_secret')
    regions = conn.get_all_regions()
    regions.should.have.length_of(8)
    regions[0].name.should.equal('eu-west-1')
    regions[0].endpoint.should.equal('ec2.eu-west-1.amazonaws.com')


@mock_ec2
def test_availability_zones():
    # Just testing us-east-1 for now
    conn = boto.connect_ec2('the_key', 'the_secret')
    zones = conn.get_all_zones()
    zones.should.have.length_of(5)
    zones[0].name.should.equal('us-east-1a')
    zones[0].region_name.should.equal('us-east-1')

########NEW FILE########
__FILENAME__ = test_customer_gateways
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_customer_gateways():
    pass

########NEW FILE########
__FILENAME__ = test_dhcp_options
import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2

SAMPLE_DOMAIN_NAME = u'example.com'
SAMPLE_NAME_SERVERS = [u'10.0.0.6', u'10.0.0.7']


@mock_ec2
def test_dhcp_options_associate():
    """ associate dhcp option """
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc = conn.create_vpc("10.0.0.0/16")

    rval = conn.associate_dhcp_options(dhcp_options.id, vpc.id)
    rval.should.be.equal(True)


@mock_ec2
def test_dhcp_options_associate_invalid_dhcp_id():
    """ associate dhcp option bad dhcp options id """
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.associate_dhcp_options.when.called_with("foo", vpc.id).should.throw(EC2ResponseError)


@mock_ec2
def test_dhcp_options_associate_invalid_vpc_id():
    """ associate dhcp option invalid vpc id """
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)

    conn.associate_dhcp_options.when.called_with(dhcp_options.id, "foo").should.throw(EC2ResponseError)


@mock_ec2
def test_dhcp_options_delete_with_vpc():
    """Test deletion of dhcp options with vpc"""
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    dhcp_options_id = dhcp_options.id
    vpc = conn.create_vpc("10.0.0.0/16")

    rval = conn.associate_dhcp_options(dhcp_options_id, vpc.id)
    rval.should.be.equal(True)

    #conn.delete_dhcp_options(dhcp_options_id)
    conn.delete_dhcp_options.when.called_with(dhcp_options_id).should.throw(EC2ResponseError)
    vpc.delete()

    conn.get_all_dhcp_options.when.called_with([dhcp_options_id]).should.throw(EC2ResponseError)


@mock_ec2
def test_create_dhcp_options():
    """Create most basic dhcp option"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    dhcp_option = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    dhcp_option.options[u'domain-name'][0].should.be.equal(SAMPLE_DOMAIN_NAME)
    dhcp_option.options[u'domain-name-servers'][0].should.be.equal(SAMPLE_NAME_SERVERS[0])
    dhcp_option.options[u'domain-name-servers'][1].should.be.equal(SAMPLE_NAME_SERVERS[1])


@mock_ec2
def test_create_dhcp_options_invalid_options():
    """Create invalid dhcp options"""
    conn = boto.connect_vpc('the_key', 'the_secret')
    servers = ["f", "f", "f", "f", "f"]
    conn.create_dhcp_options.when.called_with(ntp_servers=servers).should.throw(EC2ResponseError)
    conn.create_dhcp_options.when.called_with(netbios_node_type="0").should.throw(EC2ResponseError)


@mock_ec2
def test_describe_dhcp_options():
    """Test dhcp options lookup by id"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    dhcp_option = conn.create_dhcp_options()
    dhcp_options = conn.get_all_dhcp_options([dhcp_option.id])
    dhcp_options.should.be.length_of(1)

    dhcp_options = conn.get_all_dhcp_options()
    dhcp_options.should.be.length_of(1)


@mock_ec2
def test_describe_dhcp_options_invalid_id():
    """get error on invalid dhcp_option_id lookup"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    conn.get_all_dhcp_options.when.called_with(["1"]).should.throw(EC2ResponseError)


@mock_ec2
def test_delete_dhcp_options():
    """delete dhcp option"""
    conn = boto.connect_vpc('the_key', 'the_secret')

    dhcp_option = conn.create_dhcp_options()
    dhcp_options = conn.get_all_dhcp_options([dhcp_option.id])
    dhcp_options.should.be.length_of(1)

    conn.delete_dhcp_options(dhcp_option.id)  # .should.be.equal(True)
    conn.get_all_dhcp_options.when.called_with([dhcp_option.id]).should.throw(EC2ResponseError)


@mock_ec2
def test_delete_dhcp_options_invalid_id():
    conn = boto.connect_vpc('the_key', 'the_secret')

    conn.create_dhcp_options()
    conn.delete_dhcp_options.when.called_with("1").should.throw(EC2ResponseError)


@mock_ec2
def test_dhcp_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    dhcp_option = conn.create_dhcp_options()

    dhcp_option.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the DHCP options
    dhcp_option = conn.get_all_dhcp_options()[0]
    dhcp_option.tags.should.have.length_of(1)
    dhcp_option.tags["a key"].should.equal("some value")

########NEW FILE########
__FILENAME__ = test_ec2_core
import requests
from moto import mock_ec2


@mock_ec2
def test_not_implemented_method():
    requests.post.when.called_with(
        "https://ec2.us-east-1.amazonaws.com/",
        data={'Action': ['foobar']}
    ).should.throw(NotImplementedError)

########NEW FILE########
__FILENAME__ = test_elastic_block_store
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_create_and_delete_volume():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")

    all_volumes = conn.get_all_volumes()
    all_volumes.should.have.length_of(1)
    all_volumes[0].size.should.equal(80)
    all_volumes[0].zone.should.equal("us-east-1a")

    volume = all_volumes[0]
    volume.delete()

    conn.get_all_volumes().should.have.length_of(0)

    # Deleting something that was already deleted should throw an error
    volume.delete.when.called_with().should.throw(EC2ResponseError)


@mock_ec2
def test_volume_attach_and_detach():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    volume = conn.create_volume(80, "us-east-1a")

    volume.update()
    volume.volume_state().should.equal('available')

    volume.attach(instance.id, "/dev/sdh")

    volume.update()
    volume.volume_state().should.equal('in-use')

    volume.attach_data.instance_id.should.equal(instance.id)

    volume.detach()

    volume.update()
    volume.volume_state().should.equal('available')

    volume.attach.when.called_with(
        'i-1234abcd', "/dev/sdh").should.throw(EC2ResponseError)

    conn.detach_volume.when.called_with(
        volume.id, instance.id, "/dev/sdh").should.throw(EC2ResponseError)

    conn.detach_volume.when.called_with(
        volume.id, 'i-1234abcd', "/dev/sdh").should.throw(EC2ResponseError)


@mock_ec2
def test_create_snapshot():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")

    volume.create_snapshot('a test snapshot')

    snapshots = conn.get_all_snapshots()
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal('a test snapshot')

    # Create snapshot without description
    snapshot = volume.create_snapshot()
    conn.get_all_snapshots().should.have.length_of(2)

    snapshot.delete()
    conn.get_all_snapshots().should.have.length_of(1)

    # Deleting something that was already deleted should throw an error
    snapshot.delete.when.called_with().should.throw(EC2ResponseError)

########NEW FILE########
__FILENAME__ = test_elastic_ip_addresses
"""Test mocking of Elatic IP Address"""
import boto
from boto.exception import EC2ResponseError

import sure  # noqa

from moto import mock_ec2

import logging
import types


@mock_ec2
def test_eip_allocate_classic():
    """Allocate/release Classic EIP"""
    conn = boto.connect_ec2('the_key', 'the_secret')

    standard = conn.allocate_address()
    standard.should.be.a(boto.ec2.address.Address)
    standard.public_ip.should.be.a(types.UnicodeType)
    standard.instance_id.should.be.none
    standard.domain.should.be.equal("standard")
    standard.release()
    standard.should_not.be.within(conn.get_all_addresses())


@mock_ec2
def test_eip_allocate_vpc():
    """Allocate/release VPC EIP"""
    conn = boto.connect_ec2('the_key', 'the_secret')

    vpc = conn.allocate_address(domain="vpc")
    vpc.should.be.a(boto.ec2.address.Address)
    vpc.domain.should.be.equal("vpc")
    logging.debug("vpc alloc_id:".format(vpc.allocation_id))
    vpc.release()


@mock_ec2
def test_eip_allocate_invalid_domain():
    """Allocate EIP invalid domain"""
    conn = boto.connect_ec2('the_key', 'the_secret')

    conn.allocate_address.when.called_with(domain="bogus").should.throw(EC2ResponseError)


@mock_ec2
def test_eip_associate_classic():
    """Associate/Disassociate EIP to classic instance"""
    conn = boto.connect_ec2('the_key', 'the_secret')

    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    eip = conn.allocate_address()
    eip.instance_id.should.be.none
    conn.associate_address.when.called_with(public_ip=eip.public_ip).should.throw(EC2ResponseError)
    conn.associate_address(instance_id=instance.id, public_ip=eip.public_ip)
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]  # no .update() on address ):
    eip.instance_id.should.be.equal(instance.id)
    conn.disassociate_address(public_ip=eip.public_ip)
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]  # no .update() on address ):
    eip.instance_id.should.be.equal(u'')
    eip.release()
    eip.should_not.be.within(conn.get_all_addresses())
    eip = None

    instance.terminate()

@mock_ec2
def test_eip_associate_vpc():
    """Associate/Disassociate EIP to VPC instance"""
    conn = boto.connect_ec2('the_key', 'the_secret')

    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    eip = conn.allocate_address(domain='vpc')
    eip.instance_id.should.be.none
    conn.associate_address.when.called_with(allocation_id=eip.allocation_id).should.throw(EC2ResponseError)
    conn.associate_address(instance_id=instance.id, allocation_id=eip.allocation_id)
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]  # no .update() on address ):
    eip.instance_id.should.be.equal(instance.id)
    conn.disassociate_address(association_id=eip.association_id)
    eip = conn.get_all_addresses(addresses=[eip.public_ip])[0]  # no .update() on address ):
    eip.instance_id.should.be.equal(u'')
    eip.association_id.should.be.none
    eip.release()
    eip = None

    instance.terminate()

@mock_ec2
def test_eip_reassociate():
    """reassociate EIP"""
    conn = boto.connect_ec2('the_key', 'the_secret')

    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    eip = conn.allocate_address()
    conn.associate_address(instance_id=instance.id, public_ip=eip.public_ip)
    conn.associate_address.when.called_with(instance_id=instance.id, public_ip=eip.public_ip, allow_reassociation=False).should.throw(EC2ResponseError)
    conn.associate_address.when.called_with(instance_id=instance.id, public_ip=eip.public_ip, allow_reassociation=True).should_not.throw(EC2ResponseError)
    eip.release()
    eip = None

    instance.terminate()

@mock_ec2
def test_eip_associate_invalid_args():
    """Associate EIP, invalid args """
    conn = boto.connect_ec2('the_key', 'the_secret')

    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    eip = conn.allocate_address()
    conn.associate_address.when.called_with(instance_id=instance.id).should.throw(EC2ResponseError)

    instance.terminate()


@mock_ec2
def test_eip_disassociate_bogus_association():
    """Disassociate bogus EIP"""
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.disassociate_address.when.called_with(association_id="bogus").should.throw(EC2ResponseError)

@mock_ec2
def test_eip_release_bogus_eip():
    """Release bogus EIP"""
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.release_address.when.called_with(allocation_id="bogus").should.throw(EC2ResponseError)


@mock_ec2
def test_eip_disassociate_arg_error():
    """Invalid arguments disassociate address"""
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.disassociate_address.when.called_with().should.throw(EC2ResponseError)


@mock_ec2
def test_eip_release_arg_error():
    """Invalid arguments release address"""
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.release_address.when.called_with().should.throw(EC2ResponseError)


@mock_ec2
def test_eip_describe():
    """Listing of allocated Elastic IP Addresses."""
    conn = boto.connect_ec2('the_key', 'the_secret')
    eips = []
    number_of_classic_ips = 2
    number_of_vpc_ips = 2

    #allocate some IPs
    for _ in range(number_of_classic_ips):
        eips.append(conn.allocate_address())
    for _ in range(number_of_vpc_ips):
        eips.append(conn.allocate_address(domain='vpc'))
    len(eips).should.be.equal(number_of_classic_ips + number_of_vpc_ips)

    # Can we find each one individually?
    for eip in eips:
        if eip.allocation_id:
            lookup_addresses = conn.get_all_addresses(allocation_ids=[eip.allocation_id])
        else:
            lookup_addresses = conn.get_all_addresses(addresses=[eip.public_ip])
        len(lookup_addresses).should.be.equal(1)
        lookup_addresses[0].public_ip.should.be.equal(eip.public_ip)

    # Can we find first two when we search for them?
    lookup_addresses = conn.get_all_addresses(addresses=[eips[0].public_ip, eips[1].public_ip])
    len(lookup_addresses).should.be.equal(2)
    lookup_addresses[0].public_ip.should.be.equal(eips[0].public_ip)
    lookup_addresses[1].public_ip.should.be.equal(eips[1].public_ip)

    #Release all IPs
    for eip in eips:
        eip.release()
    len(conn.get_all_addresses()).should.be.equal(0)


@mock_ec2
def test_eip_describe_none():
    """Find nothing when seach for bogus IP"""
    conn = boto.connect_ec2('the_key', 'the_secret')
    lookup_addresses = conn.get_all_addresses(addresses=["256.256.256.256"])
    len(lookup_addresses).should.be.equal(0)



########NEW FILE########
__FILENAME__ = test_elastic_network_interfaces
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_elastic_network_interfaces():
    pass

########NEW FILE########
__FILENAME__ = test_general
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_console_output():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance_id = reservation.instances[0].id

    output = conn.get_console_output(instance_id)
    output.output.should_not.equal(None)


@mock_ec2
def test_console_output_without_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.get_console_output.when.called_with('i-1234abcd').should.throw(Exception)

########NEW FILE########
__FILENAME__ = test_instances
import base64

import boto
from boto.ec2.instance import Reservation, InstanceAttribute
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


################ Test Readme ###############
def add_servers(ami_id, count):
    conn = boto.connect_ec2()
    for index in range(count):
        conn.run_instances(ami_id)


@mock_ec2
def test_add_servers():
    add_servers('ami-1234abcd', 2)

    conn = boto.connect_ec2()
    reservations = conn.get_all_instances()
    assert len(reservations) == 2
    instance1 = reservations[0].instances[0]
    assert instance1.image_id == 'ami-1234abcd'

############################################


@mock_ec2
def test_instance_launch_and_terminate():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    reservation.should.be.a(Reservation)
    reservation.instances.should.have.length_of(1)
    instance = reservation.instances[0]
    instance.state.should.equal('pending')

    reservations = conn.get_all_instances()
    reservations.should.have.length_of(1)
    reservations[0].id.should.equal(reservation.id)
    instances = reservations[0].instances
    instances.should.have.length_of(1)
    instances[0].id.should.equal(instance.id)
    instances[0].state.should.equal('running')

    conn.terminate_instances([instances[0].id])

    reservations = conn.get_all_instances()
    instance = reservations[0].instances[0]
    instance.state.should.equal('terminated')


@mock_ec2
def test_get_instances_by_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instance1, instance2 = reservation.instances

    reservations = conn.get_all_instances(instance_ids=[instance1.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(1)
    reservation.instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(instance_ids=[instance1.id, instance2.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in reservation.instances]
    instance_ids.should.equal([instance1.id, instance2.id])

    # Call get_all_instances with a bad id should raise an error
    conn.get_all_instances.when.called_with(instance_ids=[instance1.id, "i-1234abcd"]).should.throw(
        EC2ResponseError,
        "The instance ID 'i-1234abcd' does not exist"
    )


@mock_ec2
def test_get_instances_filtering_by_state():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances

    conn.terminate_instances([instance1.id])

    reservations = conn.get_all_instances(filters={'instance-state-name': 'running'})
    reservations.should.have.length_of(1)
    # Since we terminated instance1, only instance2 and instance3 should be returned
    instance_ids = [instance.id for instance in reservations[0].instances]
    set(instance_ids).should.equal(set([instance2.id, instance3.id]))

    reservations = conn.get_all_instances([instance2.id], filters={'instance-state-name': 'running'})
    reservations.should.have.length_of(1)
    instance_ids = [instance.id for instance in reservations[0].instances]
    instance_ids.should.equal([instance2.id])

    reservations = conn.get_all_instances([instance2.id], filters={'instance-state-name': 'terminated'})
    list(reservations).should.equal([])

    # get_all_instances should still return all 3
    reservations = conn.get_all_instances()
    reservations[0].instances.should.have.length_of(3)

    conn.get_all_instances.when.called_with(filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)


@mock_ec2
def test_instance_start_and_stop():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instances = reservation.instances
    instances.should.have.length_of(2)

    instance_ids = [instance.id for instance in instances]
    stopped_instances = conn.stop_instances(instance_ids)

    for instance in stopped_instances:
        instance.state.should.equal('stopping')

    started_instances = conn.start_instances([instances[0].id])
    started_instances[0].state.should.equal('pending')


@mock_ec2
def test_instance_reboot():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    instance.reboot()
    instance.state.should.equal('pending')


@mock_ec2
def test_instance_attribute_instance_type():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.modify_attribute("instanceType", "m1.small")

    instance_attribute = instance.get_attribute("instanceType")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get('instanceType').should.equal("m1.small")


@mock_ec2
def test_instance_attribute_user_data():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.modify_attribute("userData", "this is my user data")

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("userData").should.equal("this is my user data")


@mock_ec2
def test_user_data_with_run_instance():
    user_data = "some user data"
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', user_data=user_data)
    instance = reservation.instances[0]

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    decoded_user_data = base64.decodestring(instance_attribute.get("userData"))
    decoded_user_data.should.equal("some user data")


@mock_ec2
def test_run_instance_with_security_group_name():
    conn = boto.connect_ec2('the_key', 'the_secret')
    group = conn.create_security_group('group1', "some description")

    reservation = conn.run_instances('ami-1234abcd',
                                     security_groups=['group1'])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2
def test_run_instance_with_security_group_id():
    conn = boto.connect_ec2('the_key', 'the_secret')
    group = conn.create_security_group('group1', "some description")

    reservation = conn.run_instances('ami-1234abcd',
                                     security_group_ids=[group.id])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2
def test_run_instance_with_instance_type():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', instance_type="t1.micro")
    instance = reservation.instances[0]

    instance.instance_type.should.equal("t1.micro")


@mock_ec2
def test_run_instance_with_subnet():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd',
                                     subnet_id="subnet-abcd1234")
    instance = reservation.instances[0]

    instance.subnet_id.should.equal("subnet-abcd1234")


@mock_ec2
def test_run_instance_with_keypair():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', key_name="keypair_name")
    instance = reservation.instances[0]

    instance.key_name.should.equal("keypair_name")

########NEW FILE########
__FILENAME__ = test_internet_gateways
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_internet_gateways():
    pass

########NEW FILE########
__FILENAME__ = test_ip_addresses
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_ip_addresses():
    pass

########NEW FILE########
__FILENAME__ = test_key_pairs
import boto
import sure  # noqa

from boto.exception import EC2ResponseError
from moto import mock_ec2


@mock_ec2
def test_key_pairs_empty():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0


@mock_ec2
def test_key_pairs_create():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    kps = conn.get_all_key_pairs()
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2
def test_key_pairs_create_two():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    kp = conn.create_key_pair('bar')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    kps = conn.get_all_key_pairs()
    assert len(kps) == 2
    assert kps[0].name == 'foo'
    assert kps[1].name == 'bar'
    kps = conn.get_all_key_pairs('foo')
    assert len(kps) == 1
    assert kps[0].name == 'foo'


@mock_ec2
def test_key_pairs_create_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    kp = conn.create_key_pair('foo')
    assert kp.material.startswith('---- BEGIN RSA PRIVATE KEY ----')
    assert len(conn.get_all_key_pairs()) == 1
    conn.create_key_pair.when.called_with('foo').should.throw(
        EC2ResponseError,
        "The keypair 'foo' already exists."
    )


@mock_ec2
def test_key_pairs_delete_no_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    assert len(conn.get_all_key_pairs()) == 0
    r = conn.delete_key_pair('foo')
    r.should.be.ok


@mock_ec2
def test_key_pairs_delete_exist():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.create_key_pair('foo')
    r = conn.delete_key_pair('foo')
    r.should.be.ok
    assert len(conn.get_all_key_pairs()) == 0

########NEW FILE########
__FILENAME__ = test_monitoring
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_monitoring():
    pass

########NEW FILE########
__FILENAME__ = test_network_acls
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_network_acls():
    pass

########NEW FILE########
__FILENAME__ = test_placement_groups
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_placement_groups():
    pass

########NEW FILE########
__FILENAME__ = test_reserved_instances
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_reserved_instances():
    pass

########NEW FILE########
__FILENAME__ = test_route_tables
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_route_tables():
    pass

########NEW FILE########
__FILENAME__ = test_security_groups
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_create_and_describe_security_group():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test security group', 'this is a test security group')

    security_group.name.should.equal('test security group')
    security_group.description.should.equal('this is a test security group')

    # Trying to create another group with the same name should throw an error
    conn.create_security_group.when.called_with('test security group', 'this is a test security group').should.throw(EC2ResponseError)

    all_groups = conn.get_all_security_groups()
    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal('test security group')


@mock_ec2
def test_create_security_group_without_description_raises_error():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.create_security_group.when.called_with('test security group', '').should.throw(EC2ResponseError)


@mock_ec2
def test_create_and_describe_vpc_security_group():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = 'vpc-5300000c'
    security_group = conn.create_security_group('test security group', 'this is a test security group', vpc_id=vpc_id)

    security_group.vpc_id.should.equal(vpc_id)

    security_group.name.should.equal('test security group')
    security_group.description.should.equal('this is a test security group')

    # Trying to create another group with the same name in the same VPC should throw an error
    conn.create_security_group.when.called_with('test security group', 'this is a test security group', vpc_id).should.throw(EC2ResponseError)

    all_groups = conn.get_all_security_groups()

    all_groups[0].vpc_id.should.equal(vpc_id)

    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal('test security group')


@mock_ec2
def test_create_two_security_groups_with_same_name_in_different_vpc():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = 'vpc-5300000c'
    vpc_id2 = 'vpc-5300000d'

    conn.create_security_group('test security group', 'this is a test security group', vpc_id)
    conn.create_security_group('test security group', 'this is a test security group', vpc_id2)

    all_groups = conn.get_all_security_groups()

    all_groups.should.have.length_of(2)
    all_groups[0].name.should.equal('test security group')
    all_groups[1].name.should.equal('test security group')


@mock_ec2
def test_deleting_security_groups():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group1 = conn.create_security_group('test1', 'test1')
    conn.create_security_group('test2', 'test2')

    conn.get_all_security_groups().should.have.length_of(2)

    # Deleting a group that doesn't exist should throw an error
    conn.delete_security_group.when.called_with('foobar').should.throw(EC2ResponseError)

    # Delete by name
    conn.delete_security_group('test2')
    conn.get_all_security_groups().should.have.length_of(1)

    # Delete by group id
    conn.delete_security_group(group_id=security_group1.id)
    conn.get_all_security_groups().should.have.length_of(0)


@mock_ec2
def test_delete_security_group_in_vpc():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = "vpc-12345"
    security_group1 = conn.create_security_group('test1', 'test1', vpc_id)

    # this should not throw an exception
    conn.delete_security_group(group_id=security_group1.id)


@mock_ec2
def test_authorize_ip_range_and_revoke():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test', 'test')

    success = security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32")
    assert success.should.be.true

    security_group = conn.get_all_security_groups()[0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].cidr_ip.should.equal("123.123.123.123/32")

    # Wrong Cidr should throw error
    security_group.revoke.when.called_with(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.122/32").should.throw(EC2ResponseError)

    # Actually revoke
    security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32")

    security_group = conn.get_all_security_groups()[0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_authorize_other_group_and_revoke():
    conn = boto.connect_ec2('the_key', 'the_secret')
    security_group = conn.create_security_group('test', 'test')
    other_security_group = conn.create_security_group('other', 'other')
    wrong_group = conn.create_security_group('wrong', 'wrong')

    success = security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)
    assert success.should.be.true

    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test'][0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].group_id.should.equal(other_security_group.id)

    # Wrong source group should throw error
    security_group.revoke.when.called_with(ip_protocol="tcp", from_port="22", to_port="2222", src_group=wrong_group).should.throw(EC2ResponseError)

    # Actually revoke
    security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)

    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test'][0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_authorize_group_in_vpc():
    conn = boto.connect_ec2('the_key', 'the_secret')
    vpc_id = "vpc-12345"

    # create 2 groups in a vpc
    security_group = conn.create_security_group('test1', 'test1', vpc_id)
    other_security_group = conn.create_security_group('test2', 'test2', vpc_id)

    success = security_group.authorize(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)
    success.should.be.true

    # Check that the rule is accurate
    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test1'][0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].group_id.should.equal(other_security_group.id)

    # Now revome the rule
    success = security_group.revoke(ip_protocol="tcp", from_port="22", to_port="2222", src_group=other_security_group)
    success.should.be.true

    # And check that it gets revoked
    security_group = [group for group in conn.get_all_security_groups() if group.name == 'test1'][0]
    security_group.rules.should.have.length_of(0)

########NEW FILE########
__FILENAME__ = test_server
import re
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_ec2_server_get():
    backend = server.create_backend_app("ec2")
    test_client = backend.test_client()

    res = test_client.get('/?Action=RunInstances&ImageId=ami-60a54009')

    groups = re.search("<instanceId>(.*)</instanceId>", res.data)
    instance_id = groups.groups()[0]

    res = test_client.get('/?Action=DescribeInstances')
    res.data.should.contain(instance_id)

########NEW FILE########
__FILENAME__ = test_spot_instances
import datetime

import boto
import sure  # noqa

from moto import mock_ec2
from moto.core.utils import iso_8601_datetime


@mock_ec2
def test_request_spot_instances():
    conn = boto.connect_ec2()

    conn.create_security_group('group1', 'description')
    conn.create_security_group('group2', 'description')

    start = iso_8601_datetime(datetime.datetime(2013, 1, 1))
    end = iso_8601_datetime(datetime.datetime(2013, 1, 2))

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234', count=1, type='one-time',
        valid_from=start, valid_until=end, launch_group="the-group",
        availability_zone_group='my-group', key_name="test",
        security_groups=['group1', 'group2'], user_data="some test data",
        instance_type='m1.small', placement='us-east-1c',
        kernel_id="test-kernel", ramdisk_id="test-ramdisk",
        monitoring_enabled=True, subnet_id="subnet123",
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("open")
    request.price.should.equal(0.5)
    request.launch_specification.image_id.should.equal('ami-abcd1234')
    request.type.should.equal('one-time')
    request.valid_from.should.equal(start)
    request.valid_until.should.equal(end)
    request.launch_group.should.equal("the-group")
    request.availability_zone_group.should.equal('my-group')
    request.launch_specification.key_name.should.equal("test")
    security_group_names = [group.name for group in request.launch_specification.groups]
    set(security_group_names).should.equal(set(['group1', 'group2']))
    request.launch_specification.instance_type.should.equal('m1.small')
    request.launch_specification.placement.should.equal('us-east-1c')
    request.launch_specification.kernel.should.equal("test-kernel")
    request.launch_specification.ramdisk.should.equal("test-ramdisk")
    request.launch_specification.subnet_id.should.equal("subnet123")


@mock_ec2
def test_request_spot_instances_default_arguments():
    """
    Test that moto set the correct default arguments
    """
    conn = boto.connect_ec2()

    request = conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)
    request = requests[0]

    request.state.should.equal("open")
    request.price.should.equal(0.5)
    request.launch_specification.image_id.should.equal('ami-abcd1234')
    request.type.should.equal('one-time')
    request.valid_from.should.equal(None)
    request.valid_until.should.equal(None)
    request.launch_group.should.equal(None)
    request.availability_zone_group.should.equal(None)
    request.launch_specification.key_name.should.equal(None)
    security_group_names = [group.name for group in request.launch_specification.groups]
    security_group_names.should.equal(["default"])
    request.launch_specification.instance_type.should.equal('m1.small')
    request.launch_specification.placement.should.equal(None)
    request.launch_specification.kernel.should.equal(None)
    request.launch_specification.ramdisk.should.equal(None)
    request.launch_specification.subnet_id.should.equal(None)


@mock_ec2
def test_cancel_spot_instance_request():
    conn = boto.connect_ec2()

    conn.request_spot_instances(
        price=0.5, image_id='ami-abcd1234',
    )

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(1)

    conn.cancel_spot_instance_requests([requests[0].id])

    requests = conn.get_all_spot_instance_requests()
    requests.should.have.length_of(0)

########NEW FILE########
__FILENAME__ = test_subnets
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_subnets():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(1)

    conn.delete_subnet(subnet.id)

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(0)

    conn.delete_subnet.when.called_with(
        subnet.id).should.throw(EC2ResponseError)


@mock_ec2
def test_subnet_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    subnet.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the subnet
    subnet = conn.get_all_subnets()[0]
    subnet.tags.should.have.length_of(1)
    subnet.tags["a key"].should.equal("some value")

########NEW FILE########
__FILENAME__ = test_tags
import itertools

import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_instance_launch_and_terminate():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.add_tag("a key", "some value")

    tags = conn.get_all_tags()
    tag = tags[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    instance.remove_tag("a key")
    conn.get_all_tags().should.have.length_of(0)


@mock_ec2
def test_instance_launch_and_retrieve_all_instances():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.add_tag("a key", "some value")
    chain = itertools.chain.from_iterable
    existing_instances = list(chain([res.instances for res in conn.get_all_instances()]))
    existing_instances.should.have.length_of(1)
    existing_instance = existing_instances[0]
    existing_instance.tags["a key"].should.equal("some value")

########NEW FILE########
__FILENAME__ = test_virtual_private_gateways
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_virtual_private_gateways():
    pass

########NEW FILE########
__FILENAME__ = test_vm_export
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_vm_export():
    pass

########NEW FILE########
__FILENAME__ = test_vm_import
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_vm_import():
    pass

########NEW FILE########
__FILENAME__ = test_vpcs
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_vpcs():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    vpc.cidr_block.should.equal('10.0.0.0/16')

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(1)

    vpc.delete()

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(0)

    conn.delete_vpc.when.called_with(
        "vpc-1234abcd").should.throw(EC2ResponseError)


@mock_ec2
def test_vpc_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    vpc.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the vpc
    vpc = conn.get_all_vpcs()[0]
    vpc.tags.should.have.length_of(1)
    vpc.tags["a key"].should.equal("some value")

########NEW FILE########
__FILENAME__ = test_vpn_connections
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_vpn_connections():
    pass

########NEW FILE########
__FILENAME__ = test_windows
import boto
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_windows():
    pass

########NEW FILE########
__FILENAME__ = test_elb
import boto
from boto.ec2.elb import HealthCheck
import sure  # noqa

from moto import mock_elb, mock_ec2


@mock_elb
def test_create_load_balancer():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)

    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    balancer.name.should.equal("my-lb")
    set(balancer.availability_zones).should.equal(set(['us-east-1a', 'us-east-1b']))
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    listener2 = balancer.listeners[1]
    listener2.load_balancer_port.should.equal(443)
    listener2.instance_port.should.equal(8443)
    listener2.protocol.should.equal("TCP")


@mock_elb
def test_get_load_balancers_by_name():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb1', zones, ports)
    conn.create_load_balancer('my-lb2', zones, ports)
    conn.create_load_balancer('my-lb3', zones, ports)

    conn.get_all_load_balancers().should.have.length_of(3)
    conn.get_all_load_balancers(load_balancer_names=['my-lb1']).should.have.length_of(1)
    conn.get_all_load_balancers(load_balancer_names=['my-lb1', 'my-lb2']).should.have.length_of(2)


@mock_elb
def test_delete_load_balancer():
    conn = boto.connect_elb()

    zones = ['us-east-1a']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)

    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(1)

    conn.delete_load_balancer("my-lb")
    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(0)


@mock_elb
def test_create_health_check():
    conn = boto.connect_elb()

    hc = HealthCheck(
        interval=20,
        healthy_threshold=3,
        unhealthy_threshold=5,
        target='HTTP:8080/health',
        timeout=23,
    )

    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    lb.configure_health_check(hc)

    balancer = conn.get_all_load_balancers()[0]
    health_check = balancer.health_check
    health_check.interval.should.equal(20)
    health_check.healthy_threshold.should.equal(3)
    health_check.unhealthy_threshold.should.equal(5)
    health_check.target.should.equal('HTTP:8080/health')
    health_check.timeout.should.equal(23)


@mock_ec2
@mock_elb
def test_register_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    instance_ids = [instance.id for instance in balancer.instances]
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


@mock_ec2
@mock_elb
def test_deregister_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    balancer.instances.should.have.length_of(2)
    balancer.deregister_instances([instance_id1])

    balancer.instances.should.have.length_of(1)
    balancer.instances[0].id.should.equal(instance_id2)

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_elb_describe_instances():
    backend = server.create_backend_app("elb")
    test_client = backend.test_client()

    res = test_client.get('/?Action=DescribeLoadBalancers')

    res.data.should.contain('DescribeLoadBalancersResponse')

########NEW FILE########
__FILENAME__ = test_emr
import boto
from boto.emr.instance_group import InstanceGroup
from boto.emr.step import StreamingStep
import sure  # noqa

from moto import mock_emr
from tests.helpers import requires_boto_gte


@mock_emr
def test_create_job_flow():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    step2 = StreamingStep(
        name='My wordcount example2',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input2',
        output='s3n://output_bucket/output/wordcount_output2'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        master_instance_type='m1.medium',
        slave_instance_type='m1.small',
        steps=[step1, step2],
    )

    job_flow = conn.describe_jobflow(job_id)
    job_flow.state.should.equal('STARTING')
    job_flow.jobflowid.should.equal(job_id)
    job_flow.name.should.equal('My jobflow')
    job_flow.masterinstancetype.should.equal('m1.medium')
    job_flow.slaveinstancetype.should.equal('m1.small')
    job_flow.loguri.should.equal('s3://some_bucket/jobflow_logs')
    job_flow.visibletoallusers.should.equal('False')
    int(job_flow.normalizedinstancehours).should.equal(0)
    job_step = job_flow.steps[0]
    job_step.name.should.equal('My wordcount example')
    job_step.state.should.equal('STARTING')
    args = [arg.value for arg in job_step.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input',
        '-output',
        's3n://output_bucket/output/wordcount_output',
    ])

    job_step2 = job_flow.steps[1]
    job_step2.name.should.equal('My wordcount example2')
    job_step2.state.should.equal('PENDING')
    args = [arg.value for arg in job_step2.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input2',
        '-output',
        's3n://output_bucket/output/wordcount_output2',
    ])


@requires_boto_gte("2.8")
@mock_emr
def test_create_job_flow_with_new_params():
    # Test that run_jobflow works with newer params
    conn = boto.connect_emr()

    conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        master_instance_type='m1.medium',
        slave_instance_type='m1.small',
        job_flow_role='some-role-arn',
        steps=[],
    )


@mock_emr
def test_create_job_flow_visible_to_all_users():
    conn = boto.connect_emr()

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        job_flow_role='some-role-arn',
        steps=[],
        visible_to_all_users=True,
    )
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('True')


@mock_emr
def test_terminate_job_flow():
    conn = boto.connect_emr()
    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[]
    )

    flow = conn.describe_jobflows()[0]
    flow.state.should.equal('STARTING')
    conn.terminate_jobflow(job_id)
    flow = conn.describe_jobflows()[0]
    flow.state.should.equal('TERMINATED')


@mock_emr
def test_add_steps_to_flow():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[step1]
    )

    job_flow = conn.describe_jobflow(job_id)
    job_flow.state.should.equal('STARTING')
    job_flow.jobflowid.should.equal(job_id)
    job_flow.name.should.equal('My jobflow')
    job_flow.loguri.should.equal('s3://some_bucket/jobflow_logs')

    step2 = StreamingStep(
        name='My wordcount example2',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input2',
        output='s3n://output_bucket/output/wordcount_output2'
    )

    conn.add_jobflow_steps(job_id, [step2])

    job_flow = conn.describe_jobflow(job_id)
    job_step = job_flow.steps[0]
    job_step.name.should.equal('My wordcount example')
    job_step.state.should.equal('STARTING')
    args = [arg.value for arg in job_step.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input',
        '-output',
        's3n://output_bucket/output/wordcount_output',
    ])

    job_step2 = job_flow.steps[1]
    job_step2.name.should.equal('My wordcount example2')
    job_step2.state.should.equal('PENDING')
    args = [arg.value for arg in job_step2.args]
    args.should.equal([
        '-mapper',
        's3n://elasticmapreduce/samples/wordcount/wordSplitter2.py',
        '-reducer',
        'aggregate',
        '-input',
        's3n://elasticmapreduce/samples/wordcount/input2',
        '-output',
        's3n://output_bucket/output/wordcount_output2',
    ])


@mock_emr
def test_create_instance_groups():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[step1],
    )

    instance_group = InstanceGroup(6, 'TASK', 'c1.medium', 'SPOT', 'spot-0.07', '0.07')
    instance_group = conn.add_instance_groups(job_id, [instance_group])
    instance_group_id = instance_group.instancegroupids
    job_flow = conn.describe_jobflows()[0]
    int(job_flow.instancecount).should.equal(6)
    instance_group = job_flow.instancegroups[0]
    instance_group.instancegroupid.should.equal(instance_group_id)
    int(instance_group.instancerunningcount).should.equal(6)
    instance_group.instancerole.should.equal('TASK')
    instance_group.instancetype.should.equal('c1.medium')
    instance_group.market.should.equal('SPOT')
    instance_group.name.should.equal('spot-0.07')
    instance_group.bidprice.should.equal('0.07')


@mock_emr
def test_modify_instance_groups():
    conn = boto.connect_emr()

    step1 = StreamingStep(
        name='My wordcount example',
        mapper='s3n://elasticmapreduce/samples/wordcount/wordSplitter.py',
        reducer='aggregate',
        input='s3n://elasticmapreduce/samples/wordcount/input',
        output='s3n://output_bucket/output/wordcount_output'
    )

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        steps=[step1]
    )

    instance_group1 = InstanceGroup(6, 'TASK', 'c1.medium', 'SPOT', 'spot-0.07', '0.07')
    instance_group2 = InstanceGroup(6, 'TASK', 'c1.medium', 'SPOT', 'spot-0.07', '0.07')
    instance_group = conn.add_instance_groups(job_id, [instance_group1, instance_group2])
    instance_group_ids = instance_group.instancegroupids.split(",")

    job_flow = conn.describe_jobflows()[0]
    int(job_flow.instancecount).should.equal(12)
    instance_group = job_flow.instancegroups[0]
    int(instance_group.instancerunningcount).should.equal(6)

    conn.modify_instance_groups(instance_group_ids, [2, 3])

    job_flow = conn.describe_jobflows()[0]
    int(job_flow.instancecount).should.equal(5)
    instance_group1 = [
        group for group
        in job_flow.instancegroups
        if group.instancegroupid == instance_group_ids[0]
    ][0]
    int(instance_group1.instancerunningcount).should.equal(2)
    instance_group2 = [
        group for group
        in job_flow.instancegroups
        if group.instancegroupid == instance_group_ids[1]
    ][0]
    int(instance_group2.instancerunningcount).should.equal(3)


@mock_emr
def test_set_visible_to_all_users():
    conn = boto.connect_emr()

    job_id = conn.run_jobflow(
        name='My jobflow',
        log_uri='s3://some_bucket/jobflow_logs',
        job_flow_role='some-role-arn',
        steps=[],
        visible_to_all_users=False,
    )
    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('False')

    conn.set_visible_to_all_users(job_id, True)

    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('True')

    conn.set_visible_to_all_users(job_id, False)

    job_flow = conn.describe_jobflow(job_id)
    job_flow.visibletoallusers.should.equal('False')

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_describe_jobflows():
    backend = server.create_backend_app("emr")
    test_client = backend.test_client()

    res = test_client.get('/?Action=DescribeJobFlows')

    res.data.should.contain('<DescribeJobFlowsResult>')
    res.data.should.contain('<JobFlows>')

########NEW FILE########
__FILENAME__ = test_iam
import boto

import sure  # noqa

from moto import mock_iam


@mock_iam()
def test_create_role_and_instance_profile():
    conn = boto.connect_iam()
    conn.create_instance_profile("my-profile", path="my-path")
    conn.create_role("my-role", assume_role_policy_document="some policy", path="my-path")

    conn.add_role_to_instance_profile("my-profile", "my-role")

    role = conn.get_role("my-role")
    role.path.should.equal("my-path")
    role.assume_role_policy_document.should.equal("some policy")

    profile = conn.get_instance_profile("my-profile")
    profile.path.should.equal("my-path")
    role_from_profile = profile.roles.values()[0]
    role_from_profile['role_id'].should.equal(role.role_id)
    role_from_profile['role_name'].should.equal("my-role")

    conn.list_roles().roles[0].role_name.should.equal('my-role')
    conn.list_instance_profiles().instance_profiles[0].instance_profile_name.should.equal("my-profile")

########NEW FILE########
__FILENAME__ = test_route53
import urllib2

import boto
from boto.exception import S3ResponseError
from boto.s3.key import Key
from boto.route53.record import ResourceRecordSets
from freezegun import freeze_time
import requests

import sure  # noqa

from moto import mock_route53


@mock_route53
def test_hosted_zone():
    conn = boto.connect_route53('the_key', 'the_secret')
    firstzone = conn.create_hosted_zone("testdns.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    secondzone = conn.create_hosted_zone("testdns1.aws.com")
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(2)

    id1 = firstzone["CreateHostedZoneResponse"]["HostedZone"]["Id"]
    zone = conn.get_hosted_zone(id1)
    zone["GetHostedZoneResponse"]["HostedZone"]["Name"].should.equal("testdns.aws.com")

    conn.delete_hosted_zone(id1)
    zones = conn.get_all_hosted_zones()
    len(zones["ListHostedZonesResponse"]["HostedZones"]).should.equal(1)

    conn.get_hosted_zone.when.called_with("abcd").should.throw(boto.route53.exception.DNSServerError, "404 Not Found")


@mock_route53
def test_rrset():
    conn = boto.connect_route53('the_key', 'the_secret')

    conn.get_all_rrsets.when.called_with("abcd", type="A").\
                should.throw(boto.route53.exception.DNSServerError, "404 Not Found")

    zone = conn.create_hosted_zone("testdns.aws.com")
    zoneid = zone["CreateHostedZoneResponse"]["HostedZone"]["Id"]

    changes = ResourceRecordSets(conn, zoneid)
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("1.2.3.4")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('1.2.3.4')

    rrsets = conn.get_all_rrsets(zoneid, type="CNAME")
    rrsets.should.have.length_of(0)

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    change = changes.add_change("CREATE", "foo.bar.testdns.aws.com", "A")
    change.add_value("5.6.7.8")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid, type="A")
    rrsets.should.have.length_of(1)
    rrsets[0].resource_records[0].should.equal('5.6.7.8')

    changes = ResourceRecordSets(conn, zoneid)
    changes.add_change("DELETE", "foo.bar.testdns.aws.com", "A")
    changes.commit()

    rrsets = conn.get_all_rrsets(zoneid)
    rrsets.should.have.length_of(0)

########NEW FILE########
__FILENAME__ = test_s3
import urllib2
from io import BytesIO

import boto
from boto.exception import S3CreateError, S3ResponseError
from boto.s3.key import Key
from freezegun import freeze_time
import requests

import sure  # noqa

from moto import mock_s3


class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        conn = boto.connect_s3('the_key', 'the_secret')
        bucket = conn.get_bucket('mybucket')
        k = Key(bucket)
        k.key = self.name
        k.set_contents_from_string(self.value)


@mock_s3
def test_my_model_save():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket('mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.get_bucket('mybucket').get_key('steve').get_contents_as_string().should.equal('is awesome')


@mock_s3
def test_key_etag():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket('mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.get_bucket('mybucket').get_key('steve').etag.should.equal(
        '"d32bda93738f7e03adb22e66c90fbc04"')


@mock_s3
def test_multipart_upload_too_small():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    multipart.upload_part_from_file(BytesIO('hello'), 1)
    multipart.upload_part_from_file(BytesIO('world'), 2)
    # Multipart with total size under 5MB is refused
    multipart.complete_upload.should.throw(S3ResponseError)


@mock_s3
def test_multipart_upload():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = '0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = '1'
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + part2)


@mock_s3
def test_multipart_upload_with_copy_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "original-key"
    key.set_contents_from_string("key_value")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = '0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.copy_part_from_key("foobar", "original-key", 2)
    multipart.complete_upload()
    bucket.get_key("the-key").get_contents_as_string().should.equal(part1 + "key_value")


@mock_s3
def test_multipart_upload_cancel():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = '0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    multipart.cancel_upload()
    # TODO we really need some sort of assertion here, but we don't currently
    # have the ability to list mulipart uploads for a bucket.


@mock_s3
def test_multipart_etag():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('mybucket')

    multipart = bucket.initiate_multipart_upload("the-key")
    part1 = '0' * 5242880
    multipart.upload_part_from_file(BytesIO(part1), 1)
    # last part, can be less than 5 MB
    part2 = '1'
    multipart.upload_part_from_file(BytesIO(part2), 2)
    multipart.complete_upload()
    # we should get both parts as the key contents
    bucket.get_key("the-key").etag.should.equal(
        '"140f92a6df9f9e415f74a1463bcee9bb-2"')


@mock_s3
def test_list_multiparts():
    # Create Bucket so that test can run
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('mybucket')

    multipart1 = bucket.initiate_multipart_upload("one-key")
    multipart2 = bucket.initiate_multipart_upload("two-key")
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.have.length_of(2)
    dict([(u.key_name, u.id) for u in uploads]).should.equal(
        {'one-key': multipart1.id, 'two-key': multipart2.id})
    multipart2.cancel_upload()
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.have.length_of(1)
    uploads[0].key_name.should.equal("one-key")
    multipart1.cancel_upload()
    uploads = bucket.get_all_multipart_uploads()
    uploads.should.be.empty


@mock_s3
def test_missing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    bucket.get_key("the-key").should.equal(None)


@mock_s3
def test_missing_key_urllib2():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")

    urllib2.urlopen.when.called_with("http://foobar.s3.amazonaws.com/the-key").should.throw(urllib2.HTTPError)


@mock_s3
def test_empty_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("")

    bucket.get_key("the-key").get_contents_as_string().should.equal('')


@mock_s3
def test_empty_key_set_on_existing_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar")

    bucket.get_key("the-key").get_contents_as_string().should.equal('foobar')

    key.set_contents_from_string("")
    bucket.get_key("the-key").get_contents_as_string().should.equal('')


@mock_s3
def test_large_key_save():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar" * 100000)

    bucket.get_key("the-key").get_contents_as_string().should.equal('foobar' * 100000)


@mock_s3
def test_copy_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key')

    bucket.get_key("the-key").get_contents_as_string().should.equal("some value")
    bucket.get_key("new-key").get_contents_as_string().should.equal("some value")


@mock_s3
def test_set_metadata():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = 'the-key'
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("Testval")

    bucket.get_key('the-key').get_metadata('md').should.equal('Metadatastring')


@mock_s3
def test_copy_key_replace_metadata():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key',
                    metadata={'momd': 'Mometadatastring'})

    bucket.get_key("new-key").get_metadata('md').should.be.none
    bucket.get_key("new-key").get_metadata('momd').should.equal('Mometadatastring')


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    conn = boto.connect_s3()
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    rs = bucket.get_all_keys()
    rs[0].last_modified.should.equal('2012-01-01T12:00:00Z')

    bucket.get_key("the-key").last_modified.should.equal('Sun, 01 Jan 2012 12:00:00 GMT')


@mock_s3
def test_missing_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket').should.throw(S3ResponseError)


@mock_s3
def test_bucket_with_dash():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket-test').should.throw(S3ResponseError)


@mock_s3
def test_create_existing_bucket():
    "Trying to create a bucket that already exists should raise an Error"
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")
    conn.create_bucket.when.called_with('foobar').should.throw(S3CreateError)


@mock_s3
def test_bucket_deletion():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    # Try to delete a bucket that still has keys
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    bucket.delete_key("the-key")
    conn.delete_bucket("foobar")

    # Get non-existing bucket
    conn.get_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    # Delete non-existant bucket
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)


@mock_s3
def test_get_all_buckets():
    conn = boto.connect_s3('the_key', 'the_secret')
    conn.create_bucket("foobar")
    conn.create_bucket("foobar2")
    buckets = conn.get_all_buckets()

    buckets.should.have.length_of(2)


@mock_s3
def test_post_to_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://foobar.s3.amazonaws.com/", {
        'key': 'the-key',
        'file': 'nothing'
    })

    bucket.get_key('the-key').get_contents_as_string().should.equal('nothing')


@mock_s3
def test_post_with_metadata_to_bucket():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://foobar.s3.amazonaws.com/", {
        'key': 'the-key',
        'file': 'nothing',
        'x-amz-meta-test': 'metadata'
    })

    bucket.get_key('the-key').get_metadata('test').should.equal('metadata')

@mock_s3
def test_delete_keys():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')

    Key(bucket=bucket, name='file1').set_contents_from_string('abc')
    Key(bucket=bucket, name='file2').set_contents_from_string('abc')
    Key(bucket=bucket, name='file3').set_contents_from_string('abc')
    Key(bucket=bucket, name='file4').set_contents_from_string('abc')

    result = bucket.delete_keys(['file2', 'file3'])
    
    result.deleted.should.have.length_of(2)
    result.errors.should.have.length_of(0)
    keys = bucket.get_all_keys()
    keys.should.have.length_of(2)
    keys[0].name.should.equal('file1')

@mock_s3
def test_delete_keys_with_invalid():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket('foobar')

    Key(bucket=bucket, name='file1').set_contents_from_string('abc')
    Key(bucket=bucket, name='file2').set_contents_from_string('abc')
    Key(bucket=bucket, name='file3').set_contents_from_string('abc')
    Key(bucket=bucket, name='file4').set_contents_from_string('abc')

    result = bucket.delete_keys(['abc', 'file3'])

    result.deleted.should.have.length_of(1)
    result.errors.should.have.length_of(1)
    keys = bucket.get_all_keys()
    keys.should.have.length_of(3)
    keys[0].name.should.equal('file1')

@mock_s3
def test_bucket_method_not_implemented():
    requests.patch.when.called_with("https://foobar.s3.amazonaws.com/").should.throw(NotImplementedError)


@mock_s3
def test_key_method_not_implemented():
    requests.post.when.called_with("https://foobar.s3.amazonaws.com/foo").should.throw(NotImplementedError)


@mock_s3
def test_bucket_name_with_dot():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('firstname.lastname')

    k = Key(bucket, 'somekey')
    k.set_contents_from_string('somedata')


@mock_s3
def test_key_with_special_characters():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_list_keys_2/x?y')
    key.set_contents_from_string('value1')

    key_list = bucket.list('test_list_keys_2/', '/')
    keys = [x for x in key_list]
    keys[0].name.should.equal("test_list_keys_2/x?y")


@mock_s3
def test_bucket_key_listing_order():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket')
    prefix = 'toplevel/'

    def store(name):
        k = Key(bucket, prefix + name)
        k.set_contents_from_string('somedata')

    names = ['x/key', 'y.key1', 'y.key2', 'y.key3', 'x/y/key', 'x/y/z/key']

    for name in names:
        store(name)

    delimiter = None
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key',
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'
    ])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3', 'toplevel/x/'
    ])

    # Test delimiter with no prefix
    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix=None, delimiter=delimiter)]
    keys.should.equal(['toplevel'])

    delimiter = None
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal([u'toplevel/x/key', u'toplevel/x/y/key', u'toplevel/x/y/z/key'])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal([u'toplevel/x/'])


@mock_s3
def test_key_with_reduced_redundancy():
    conn = boto.connect_s3()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_rr_key')
    key.set_contents_from_string('value1', reduced_redundancy=True)
    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    list(bucket)[0].storage_class.should.equal('REDUCED_REDUNDANCY')


@mock_s3
def test_copy_key_reduced_redundancy():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key', storage_class='REDUCED_REDUNDANCY')

    # we use the bucket iterator because of:
    # https:/github.com/boto/boto/issues/1173
    keys = dict([(k.name, k) for k in bucket])
    keys['new-key'].storage_class.should.equal("REDUCED_REDUNDANCY")
    keys['the-key'].storage_class.should.equal("STANDARD")


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_restore_key():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    list(bucket)[0].ongoing_restore.should.be.none
    key.restore(1)
    key = bucket.get_key('the-key')
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Mon, 02 Jan 2012 12:00:00 GMT")
    key.restore(2)
    key = bucket.get_key('the-key')
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Tue, 03 Jan 2012 12:00:00 GMT")


@freeze_time("2012-01-01 12:00:00")
@mock_s3
def test_restore_key_headers():
    conn = boto.connect_s3('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")
    key.restore(1, headers={'foo': 'bar'})
    key = bucket.get_key('the-key')
    key.ongoing_restore.should_not.be.none
    key.ongoing_restore.should.be.false
    key.expiry_date.should.equal("Mon, 02 Jan 2012 12:00:00 GMT")

########NEW FILE########
__FILENAME__ = test_s3_utils
from sure import expect
from moto.s3.utils import bucket_name_from_url


def test_base_url():
    expect(bucket_name_from_url('https://s3.amazonaws.com/')).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url('https://wfoobar.localhost:5000/abc')).should.equal("wfoobar")


def test_localhost_without_bucket():
    expect(bucket_name_from_url('https://www.localhost:5000/def')).should.equal(None)

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_s3_server_get():
    backend = server.create_backend_app("s3")
    test_client = backend.test_client()

    res = test_client.get('/')

    res.data.should.contain('ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    backend = server.create_backend_app("s3")
    test_client = backend.test_client()

    res = test_client.put('/', 'http://foobaz.localhost:5000/')
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain('<Name>foobaz</Name>')

    res = test_client.get('/', 'http://foobaz.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.contain("ListBucketResult")

    res = test_client.put('/bar', 'http://foobaz.localhost:5000/', data='test value')
    res.status_code.should.equal(200)

    res = test_client.get('/bar', 'http://foobaz.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal("test value")


def test_s3_server_post_to_bucket():
    backend = server.create_backend_app("s3")
    test_client = backend.test_client()

    res = test_client.put('/', 'http://tester.localhost:5000/')
    res.status_code.should.equal(200)

    test_client.post('/', "https://tester.localhost:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/the-key', 'http://tester.localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal("nothing")

########NEW FILE########
__FILENAME__ = test_bucket_path_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_s3_server_get():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.get('/')

    res.data.should.contain('ListAllMyBucketsResult')


def test_s3_server_bucket_create():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar', 'http://localhost:5000')
    res.status_code.should.equal(200)

    res = test_client.get('/')
    res.data.should.contain('<Name>foobar</Name>')

    res = test_client.get('/foobar', 'http://localhost:5000')
    res.status_code.should.equal(200)
    res.data.should.contain("ListBucketResult")

    res = test_client.get('/missing-bucket', 'http://localhost:5000')
    res.status_code.should.equal(404)

    res = test_client.put('/foobar/bar', 'http://localhost:5000', data='test value')
    res.status_code.should.equal(200)

    res = test_client.get('/foobar/bar', 'http://localhost:5000')
    res.status_code.should.equal(200)
    res.data.should.equal("test value")


def test_s3_server_post_to_bucket():
    backend = server.create_backend_app("s3bucket_path")
    test_client = backend.test_client()

    res = test_client.put('/foobar2', 'http://localhost:5000/')
    res.status_code.should.equal(200)

    test_client.post('/foobar2', "https://localhost:5000/", data={
        'key': 'the-key',
        'file': 'nothing'
    })

    res = test_client.get('/foobar2/the-key', 'http://localhost:5000/')
    res.status_code.should.equal(200)
    res.data.should.equal("nothing")

########NEW FILE########
__FILENAME__ = test_s3bucket_path
import urllib2

import boto
from boto.exception import S3ResponseError
from boto.s3.key import Key
from boto.s3.connection import OrdinaryCallingFormat

from freezegun import freeze_time
import requests

import sure  # noqa

from moto import mock_s3bucket_path


def create_connection(key=None, secret=None):
    return boto.connect_s3(key, secret, calling_format=OrdinaryCallingFormat())


class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        conn = create_connection('the_key', 'the_secret')
        bucket = conn.get_bucket('mybucket')
        k = Key(bucket)
        k.key = self.name
        k.set_contents_from_string(self.value)


@mock_s3bucket_path
def test_my_model_save():
    # Create Bucket so that test can run
    conn = create_connection('the_key', 'the_secret')
    conn.create_bucket('mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.get_bucket('mybucket').get_key('steve').get_contents_as_string().should.equal('is awesome')


@mock_s3bucket_path
def test_missing_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    bucket.get_key("the-key").should.equal(None)


@mock_s3bucket_path
def test_missing_key_urllib2():
    conn = create_connection('the_key', 'the_secret')
    conn.create_bucket("foobar")

    urllib2.urlopen.when.called_with("http://s3.amazonaws.com/foobar/the-key").should.throw(urllib2.HTTPError)


@mock_s3bucket_path
def test_empty_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("")

    bucket.get_key("the-key").get_contents_as_string().should.equal('')


@mock_s3bucket_path
def test_empty_key_set_on_existing_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar")

    bucket.get_key("the-key").get_contents_as_string().should.equal('foobar')

    key.set_contents_from_string("")
    bucket.get_key("the-key").get_contents_as_string().should.equal('')


@mock_s3bucket_path
def test_large_key_save():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar" * 100000)

    bucket.get_key("the-key").get_contents_as_string().should.equal('foobar' * 100000)


@mock_s3bucket_path
def test_copy_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key')

    bucket.get_key("the-key").get_contents_as_string().should.equal("some value")
    bucket.get_key("new-key").get_contents_as_string().should.equal("some value")


@mock_s3bucket_path
def test_set_metadata():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = 'the-key'
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("Testval")

    bucket.get_key('the-key').get_metadata('md').should.equal('Metadatastring')


@freeze_time("2012-01-01 12:00:00")
@mock_s3bucket_path
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    conn = create_connection()
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    rs = bucket.get_all_keys()
    rs[0].last_modified.should.equal('2012-01-01T12:00:00Z')

    bucket.get_key("the-key").last_modified.should.equal('Sun, 01 Jan 2012 12:00:00 GMT')


@mock_s3bucket_path
def test_missing_bucket():
    conn = create_connection('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket').should.throw(S3ResponseError)


@mock_s3bucket_path
def test_bucket_with_dash():
    conn = create_connection('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket-test').should.throw(S3ResponseError)


@mock_s3bucket_path
def test_bucket_deletion():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    # Try to delete a bucket that still has keys
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    bucket.delete_key("the-key")
    conn.delete_bucket("foobar")

    # Get non-existing bucket
    conn.get_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    # Delete non-existant bucket
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)


@mock_s3bucket_path
def test_get_all_buckets():
    conn = create_connection('the_key', 'the_secret')
    conn.create_bucket("foobar")
    conn.create_bucket("foobar2")
    buckets = conn.get_all_buckets()

    buckets.should.have.length_of(2)


@mock_s3bucket_path
def test_post_to_bucket():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://s3.amazonaws.com/foobar", {
        'key': 'the-key',
        'file': 'nothing'
    })

    bucket.get_key('the-key').get_contents_as_string().should.equal('nothing')


@mock_s3bucket_path
def test_post_with_metadata_to_bucket():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://s3.amazonaws.com/foobar", {
        'key': 'the-key',
        'file': 'nothing',
        'x-amz-meta-test': 'metadata'
    })

    bucket.get_key('the-key').get_metadata('test').should.equal('metadata')


@mock_s3bucket_path
def test_bucket_method_not_implemented():
    requests.patch.when.called_with("https://s3.amazonaws.com/foobar").should.throw(NotImplementedError)


@mock_s3bucket_path
def test_key_method_not_implemented():
    requests.post.when.called_with("https://s3.amazonaws.com/foobar/foo").should.throw(NotImplementedError)


@mock_s3bucket_path
def test_bucket_name_with_dot():
    conn = create_connection()
    bucket = conn.create_bucket('firstname.lastname')

    k = Key(bucket, 'somekey')
    k.set_contents_from_string('somedata')


@mock_s3bucket_path
def test_key_with_special_characters():
    conn = create_connection()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_list_keys_2/*x+?^@~!y')
    key.set_contents_from_string('value1')

    key_list = bucket.list('test_list_keys_2/', '/')
    keys = [x for x in key_list]
    keys[0].name.should.equal("test_list_keys_2/*x+?^@~!y")


@mock_s3bucket_path
def test_bucket_key_listing_order():
    conn = create_connection()
    bucket = conn.create_bucket('test_bucket')
    prefix = 'toplevel/'

    def store(name):
        k = Key(bucket, prefix + name)
        k.set_contents_from_string('somedata')

    names = ['x/key', 'y.key1', 'y.key2', 'y.key3', 'x/y/key', 'x/y/z/key']

    for name in names:
        store(name)

    delimiter = None
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key',
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'
    ])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3', 'toplevel/x/'
    ])

    # Test delimiter with no prefix
    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix=None, delimiter=delimiter)]
    keys.should.equal(['toplevel'])

    delimiter = None
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal([u'toplevel/x/key', u'toplevel/x/y/key', u'toplevel/x/y/z/key'])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal([u'toplevel/x/'])

########NEW FILE########
__FILENAME__ = test_s3bucket_path_utils
from sure import expect
from moto.s3bucket_path.utils import bucket_name_from_url


def test_base_url():
    expect(bucket_name_from_url('https://s3.amazonaws.com/')).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url('https://localhost:5000/wfoobar/abc')).should.equal("wfoobar")


def test_localhost_without_bucket():
    expect(bucket_name_from_url('https://www.localhost:5000')).should.equal(None)

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_ses_list_identities():
    backend = server.create_backend_app("ses")
    test_client = backend.test_client()

    res = test_client.get('/?Action=ListIdentities')
    res.data.should.contain("ListIdentitiesResponse")

########NEW FILE########
__FILENAME__ = test_ses
import email

import boto
from boto.exception import BotoServerError

import sure  # noqa

from moto import mock_ses


@mock_ses
def test_verify_email_identity():
    conn = boto.connect_ses('the_key', 'the_secret')
    conn.verify_email_identity("test@example.com")

    identities = conn.list_identities()
    address = identities['ListIdentitiesResponse']['ListIdentitiesResult']['Identities'][0]
    address.should.equal('test@example.com')


@mock_ses
def test_domain_verify():
    conn = boto.connect_ses('the_key', 'the_secret')

    conn.verify_domain_dkim("domain1.com")
    conn.verify_domain_identity("domain2.com")

    identities = conn.list_identities()
    domains = list(identities['ListIdentitiesResponse']['ListIdentitiesResult']['Identities'])
    domains.should.equal(['domain1.com', 'domain2.com'])


@mock_ses
def test_delete_identity():
    conn = boto.connect_ses('the_key', 'the_secret')
    conn.verify_email_identity("test@example.com")

    conn.list_identities()['ListIdentitiesResponse']['ListIdentitiesResult']['Identities'].should.have.length_of(1)
    conn.delete_identity("test@example.com")
    conn.list_identities()['ListIdentitiesResponse']['ListIdentitiesResult']['Identities'].should.have.length_of(0)


@mock_ses
def test_send_email():
    conn = boto.connect_ses('the_key', 'the_secret')

    conn.send_email.when.called_with(
        "test@example.com", "test subject",
        "test body", "test_to@example.com").should.throw(BotoServerError)

    conn.verify_email_identity("test@example.com")
    conn.send_email("test@example.com", "test subject", "test body", "test_to@example.com")

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['GetSendQuotaResponse']['GetSendQuotaResult']['SentLast24Hours'])
    sent_count.should.equal(1)
    
@mock_ses
def test_send_html_email():
    conn = boto.connect_ses('the_key', 'the_secret')

    conn.send_email.when.called_with(
        "test@example.com", "test subject",
        "<span>test body</span>", "test_to@example.com", format="html").should.throw(BotoServerError)

    conn.verify_email_identity("test@example.com")
    conn.send_email("test@example.com", "test subject", "<span>test body</span>", "test_to@example.com", format="html")

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['GetSendQuotaResponse']['GetSendQuotaResult']['SentLast24Hours'])
    sent_count.should.equal(1)

@mock_ses
def test_send_raw_email():
    conn = boto.connect_ses('the_key', 'the_secret')

    to = 'to@example.com'
    message = email.mime.multipart.MIMEMultipart()
    message['Subject'] = 'Test'
    message['From'] = 'test@example.com'
    message['To'] = to

    # Message body
    part = email.mime.text.MIMEText('test file attached')
    message.attach(part)

    # Attachment
    part = email.mime.text.MIMEText('contents of test file here')
    part.add_header('Content-Disposition', 'attachment; filename=test.txt')
    message.attach(part)

    conn.send_raw_email.when.called_with(
        source=message['From'],
        raw_message=message.as_string(),
        destinations=message['To']
    ).should.throw(BotoServerError)

    conn.verify_email_identity("test@example.com")
    conn.send_raw_email(
        source=message['From'],
        raw_message=message.as_string(),
        destinations=message['To']
    )

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['GetSendQuotaResponse']['GetSendQuotaResult']['SentLast24Hours'])
    sent_count.should.equal(1)

########NEW FILE########
__FILENAME__ = test_publishing
from urlparse import parse_qs

import boto
from freezegun import freeze_time
import httpretty
import sure  # noqa

from moto import mock_sns, mock_sqs


@mock_sqs
@mock_sns
def test_publish_to_sqs():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    sqs_conn = boto.connect_sqs()
    sqs_conn.create_queue("test-queue")

    conn.subscribe(topic_arn, "sqs", "arn:aws:sqs:us-east-1:123456789012:test-queue")

    conn.publish(topic=topic_arn, message="my message")

    queue = sqs_conn.get_queue("test-queue")
    message = queue.read(1)
    message.get_body().should.equal('my message')


@freeze_time("2013-01-01")
@mock_sns
def test_publish_to_http():
    httpretty.HTTPretty.register_uri(
        method="POST",
        uri="http://example.com/foobar",
    )

    conn = boto.connect_sns()
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    conn.subscribe(topic_arn, "http", "http://example.com/foobar")

    response = conn.publish(topic=topic_arn, message="my message", subject="my subject")
    message_id = response['PublishResponse']['PublishResult']['MessageId']

    last_request = httpretty.last_request()
    last_request.method.should.equal("POST")
    parse_qs(last_request.body).should.equal({
        "Type": ["Notification"],
        "MessageId": [message_id],
        "TopicArn": ["arn:aws:sns:us-east-1:123456789012:some-topic"],
        "Subject": ["my subject"],
        "Message": ["my message"],
        "Timestamp": ["2013-01-01T00:00:00Z"],
        "SignatureVersion": ["1"],
        "Signature": ["EXAMPLElDMXvB8r9R83tGoNn0ecwd5UjllzsvSvbItzfaMpN2nk5HVSw7XnOn/49IkxDKz8YrlH2qJXj2iZB0Zo2O71c4qQk1fMUDi3LGpij7RCW7AW9vYYsSqIKRnFS94ilu7NFhUzLiieYr4BKHpdTmdD6c0esKEYBpabxDSc="],
        "SigningCertURL": ["https://sns.us-east-1.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem"],
        "UnsubscribeURL": ["https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123456789012:some-topic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55"],
    })

########NEW FILE########
__FILENAME__ = test_server

########NEW FILE########
__FILENAME__ = test_subscriptions
import boto

import sure  # noqa

from moto import mock_sns


@mock_sns
def test_creating_subscription():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")
    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    conn.subscribe(topic_arn, "http", "http://example.com/")

    subscriptions = conn.get_all_subscriptions()["ListSubscriptionsResponse"]["ListSubscriptionsResult"]["Subscriptions"]
    subscriptions.should.have.length_of(1)
    subscription = subscriptions[0]
    subscription["TopicArn"].should.equal(topic_arn)
    subscription["Protocol"].should.equal("http")
    subscription["SubscriptionArn"].should.contain(topic_arn)
    subscription["Endpoint"].should.equal("http://example.com/")

    # Now unsubscribe the subscription
    conn.unsubscribe(subscription["SubscriptionArn"])

    # And there should be zero subscriptions left
    subscriptions = conn.get_all_subscriptions()["ListSubscriptionsResponse"]["ListSubscriptionsResult"]["Subscriptions"]
    subscriptions.should.have.length_of(0)


@mock_sns
def test_getting_subscriptions_by_topic():
    conn = boto.connect_sns()
    conn.create_topic("topic1")
    conn.create_topic("topic2")

    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topic1_arn = topics[0]['TopicArn']
    topic2_arn = topics[1]['TopicArn']

    conn.subscribe(topic1_arn, "http", "http://example1.com/")
    conn.subscribe(topic2_arn, "http", "http://example2.com/")

    topic1_subscriptions = conn.get_all_subscriptions_by_topic(topic1_arn)["ListSubscriptionsByTopicResponse"]["ListSubscriptionsByTopicResult"]["Subscriptions"]
    topic1_subscriptions.should.have.length_of(1)
    topic1_subscriptions[0]['Endpoint'].should.equal("http://example1.com/")

########NEW FILE########
__FILENAME__ = test_topics
import boto

import sure  # noqa

from moto import mock_sns
from moto.sns.models import DEFAULT_TOPIC_POLICY, DEFAULT_EFFECTIVE_DELIVERY_POLICY


@mock_sns
def test_create_and_delete_topic():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")

    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(1)
    topics[0]['TopicArn'].should.equal("arn:aws:sns:us-east-1:123456789012:some-topic")

    # Delete the topic
    conn.delete_topic(topics[0]['TopicArn'])

    # And there should now be 0 topics
    topics_json = conn.get_all_topics()
    topics = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
    topics.should.have.length_of(0)


@mock_sns
def test_topic_attributes():
    conn = boto.connect_sns()
    conn.create_topic("some-topic")

    topics_json = conn.get_all_topics()
    topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']

    attributes = conn.get_topic_attributes(topic_arn)['GetTopicAttributesResponse']['GetTopicAttributesResult']['Attributes']
    attributes["TopicArn"].should.equal("arn:aws:sns:us-east-1:123456789012:some-topic")
    attributes["Owner"].should.equal(123456789012)
    attributes["Policy"].should.equal(DEFAULT_TOPIC_POLICY)
    attributes["DisplayName"].should.equal("")
    attributes["SubscriptionsPending"].should.equal(0)
    attributes["SubscriptionsConfirmed"].should.equal(0)
    attributes["SubscriptionsDeleted"].should.equal(0)
    attributes["DeliveryPolicy"].should.equal("")
    attributes["EffectiveDeliveryPolicy"].should.equal(DEFAULT_EFFECTIVE_DELIVERY_POLICY)

    conn.set_topic_attributes(topic_arn, "Policy", {"foo": "bar"})
    conn.set_topic_attributes(topic_arn, "DisplayName", "My display name")
    conn.set_topic_attributes(topic_arn, "DeliveryPolicy", {"http": {"defaultHealthyRetryPolicy": {"numRetries": 5}}})

    attributes = conn.get_topic_attributes(topic_arn)['GetTopicAttributesResponse']['GetTopicAttributesResult']['Attributes']
    attributes["Policy"].should.equal("{'foo': 'bar'}")
    attributes["DisplayName"].should.equal("My display name")
    attributes["DeliveryPolicy"].should.equal("{'http': {'defaultHealthyRetryPolicy': {'numRetries': 5}}}")

########NEW FILE########
__FILENAME__ = test_server
import re
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_sqs_list_identities():
    backend = server.create_backend_app("sqs")
    test_client = backend.test_client()

    res = test_client.get('/?Action=ListQueues')
    res.data.should.contain("ListQueuesResponse")

    res = test_client.put('/?Action=CreateQueue&QueueName=testqueue')
    res = test_client.put('/?Action=CreateQueue&QueueName=otherqueue')

    res = test_client.get('/?Action=ListQueues&QueueNamePrefix=other')
    res.data.should_not.contain('testqueue')

    res = test_client.put(
        '/123/testqueue?MessageBody=test-message&Action=SendMessage')

    res = test_client.get(
        '/123/testqueue?Action=ReceiveMessage&MaxNumberOfMessages=1')
    message = re.search("<Body>(.*?)</Body>", res.data).groups()[0]
    message.should.equal('test-message')

########NEW FILE########
__FILENAME__ = test_sqs
import boto
from boto.exception import SQSError
from boto.sqs.message import RawMessage
import requests
import sure  # noqa

from moto import mock_sqs


@mock_sqs
def test_create_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    all_queues = conn.get_all_queues()
    all_queues[0].name.should.equal("test-queue")

    all_queues[0].get_timeout().should.equal(60)


@mock_sqs
def test_get_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    queue = conn.get_queue("test-queue")
    queue.name.should.equal("test-queue")
    queue.get_timeout().should.equal(60)

    nonexisting_queue = conn.get_queue("nonexisting_queue")
    nonexisting_queue.should.be.none


@mock_sqs
def test_get_queue_with_prefix():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("prefixa-queue")
    conn.create_queue("prefixb-queue")
    conn.create_queue("test-queue")

    conn.get_all_queues().should.have.length_of(3)

    queue = conn.get_all_queues("test-")
    queue.should.have.length_of(1)
    queue[0].name.should.equal("test-queue")


@mock_sqs
def test_delete_queue():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.get_all_queues().should.have.length_of(1)

    queue.delete()
    conn.get_all_queues().should.have.length_of(0)

    queue.delete.when.called_with().should.throw(SQSError)


@mock_sqs
def test_set_queue_attribute():
    conn = boto.connect_sqs('the_key', 'the_secret')
    conn.create_queue("test-queue", visibility_timeout=60)

    queue = conn.get_all_queues()[0]
    queue.get_timeout().should.equal(60)

    queue.set_attribute("VisibilityTimeout", 45)
    queue = conn.get_all_queues()[0]
    queue.get_timeout().should.equal(45)


@mock_sqs
def test_send_message():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message(queue, 'this is a test message')
    conn.send_message(queue, 'this is another test message')

    messages = conn.receive_message(queue, number_messages=1)
    messages[0].get_body().should.equal('this is a test message')


@mock_sqs
def test_read_message_from_queue():
    conn = boto.connect_sqs()
    queue = conn.create_queue('testqueue')
    queue.write(queue.new_message('foo bar baz'))
    message = queue.read(1)
    message.get_body().should.equal('foo bar baz')


@mock_sqs
def test_queue_length():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message(queue, 'this is a test message')
    conn.send_message(queue, 'this is another test message')
    queue.count().should.equal(2)


@mock_sqs
def test_delete_message():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message(queue, 'this is a test message')
    conn.send_message(queue, 'this is another test message')

    messages = conn.receive_message(queue, number_messages=1)
    messages[0].delete()

    queue.count().should.equal(1)


@mock_sqs
def test_send_batch_operation():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    # See https://github.com/boto/boto/issues/831
    queue.set_message_class(RawMessage)

    queue.write_batch([
        ("my_first_message", 'test message 1', 0),
        ("my_second_message", 'test message 2', 0),
        ("my_third_message", 'test message 3', 0),
    ])

    messages = queue.get_messages(3)
    messages[0].get_body().should.equal("test message 1")

    # Test that pulling more messages doesn't break anything
    messages = queue.get_messages(2)


@mock_sqs
def test_delete_batch_operation():
    conn = boto.connect_sqs('the_key', 'the_secret')
    queue = conn.create_queue("test-queue", visibility_timeout=60)

    conn.send_message_batch(queue, [
        ("my_first_message", 'test message 1', 0),
        ("my_second_message", 'test message 2', 0),
        ("my_third_message", 'test message 3', 0),
    ])

    messages = queue.get_messages(2)
    queue.delete_message_batch(messages)

    queue.count().should.equal(1)


@mock_sqs
def test_sqs_method_not_implemented():
    requests.post.when.called_with("https://sqs.amazonaws.com/?Action=[foobar]").should.throw(NotImplementedError)


@mock_sqs
def test_queue_attributes():
    conn = boto.connect_sqs('the_key', 'the_secret')

    queue_name = 'test-queue'
    visibility_timeout = 60

    queue = conn.create_queue(queue_name, visibility_timeout=visibility_timeout)

    attributes = queue.get_attributes()

    attributes['QueueArn'].should.look_like(
        'arn:aws:sqs:sqs.us-east-1:123456789012:%s' % queue_name)

    attributes['VisibilityTimeout'].should.look_like(str(visibility_timeout))

    attribute_names = queue.get_attributes().keys()
    attribute_names.should.contain('ApproximateNumberOfMessagesNotVisible')
    attribute_names.should.contain('MessageRetentionPeriod')
    attribute_names.should.contain('ApproximateNumberOfMessagesDelayed')
    attribute_names.should.contain('MaximumMessageSize')
    attribute_names.should.contain('CreatedTimestamp')
    attribute_names.should.contain('ApproximateNumberOfMessages')
    attribute_names.should.contain('ReceiveMessageWaitTimeSeconds')
    attribute_names.should.contain('DelaySeconds')
    attribute_names.should.contain('VisibilityTimeout')
    attribute_names.should.contain('LastModifiedTimestamp')
    attribute_names.should.contain('QueueArn')

########NEW FILE########
__FILENAME__ = test_server
import sure  # noqa

import moto.server as server

'''
Test the different server responses
'''


def test_sts_get_session_token():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get('/?Action=GetSessionToken')
    res.status_code.should.equal(200)
    res.data.should.contain("SessionToken")
    res.data.should.contain("AccessKeyId")


def test_sts_get_federation_token():
    backend = server.create_backend_app("sts")
    test_client = backend.test_client()

    res = test_client.get('/?Action=GetFederationToken&Name=Bob')
    res.status_code.should.equal(200)
    res.data.should.contain("SessionToken")
    res.data.should.contain("AccessKeyId")

########NEW FILE########
__FILENAME__ = test_sts
import json

import boto
from freezegun import freeze_time
import sure  # noqa

from moto import mock_sts


@freeze_time("2012-01-01 12:00:00")
@mock_sts
def test_get_session_token():
    conn = boto.connect_sts()
    token = conn.get_session_token(duration=123)

    token.expiration.should.equal('2012-01-01T12:02:03Z')
    token.session_token.should.equal("AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE")
    token.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    token.secret_key.should.equal("wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")


@freeze_time("2012-01-01 12:00:00")
@mock_sts
def test_get_federation_token():
    conn = boto.connect_sts()
    token = conn.get_federation_token(duration=123, name="Bob")

    token.credentials.expiration.should.equal('2012-01-01T12:02:03Z')
    token.credentials.session_token.should.equal("AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGdQrmGdeehM4IC1NtBmUpp2wUE8phUZampKsburEDy0KPkyQDYwT7WZ0wq5VSXDvp75YU9HFvlRd8Tx6q6fE8YQcHNVXAkiY9q6d+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA==")
    token.credentials.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    token.credentials.secret_key.should.equal("wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")
    token.federated_user_arn.should.equal("arn:aws:sts::123456789012:federated-user/Bob")
    token.federated_user_id.should.equal("123456789012:Bob")


@freeze_time("2012-01-01 12:00:00")
@mock_sts
def test_assume_role():
    conn = boto.connect_sts()

    policy = json.dumps({
        "Statement": [
            {
                "Sid": "Stmt13690092345534",
                "Action": [
                    "S3:ListBucket"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::foobar-tester"
                ]
            },
        ]
    })
    s3_role = "arn:aws:iam::123456789012:role/test-role"
    role = conn.assume_role(s3_role, "session-name", policy, duration_seconds=123)

    credentials = role.credentials
    credentials.expiration.should.equal('2012-01-01T12:02:03Z')
    credentials.session_token.should.equal("BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE")
    credentials.access_key.should.equal("AKIAIOSFODNN7EXAMPLE")
    credentials.secret_key.should.equal("aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY")

    role.user.arn.should.equal("arn:aws:iam::123456789012:role/test-role")
    role.user.assume_role_id.should.contain("session-name")

########NEW FILE########
