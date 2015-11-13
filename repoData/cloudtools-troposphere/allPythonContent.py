__FILENAME__ = CloudFront_S3
# Converted from CloudFront_S3.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.cloudfront import Distribution, DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template CloudFront_S3: Sample template "
    "showing how to create an Amazon CloudFront distribution using an "
    "S3 origin. "
    "**WARNING** This template creates an Amazon EC2 instance. "
    "You will be billed for the AWS resources used if you create "
    "a stack from this template.")

s3dnsname = t.add_parameter(Parameter(
    "S3DNSNAme",
    Description="The DNS name of an existing S3 bucket to use as the "
                "Cloudfront distribution origin",
    Type="String",
))

myDistribution = t.add_resource(Distribution(
    "myDistribution",
    DistributionConfig=DistributionConfig(
        Origins=[Origin(Id="Origin 1", DomainName=Ref(s3dnsname))],
        DefaultCacheBehavior=DefaultCacheBehavior(
            TargetOriginId="Origin 1",
            ViewerProtocolPolicy="allow-all"),
        Enabled=True
    )
))

t.add_output([
    Output("DistributionId", Value=Ref(myDistribution)),
    Output(
        "DistributionName",
        Value=Join("", ["http://", GetAtt(myDistribution, "DomainName")])),
])

print(t.to_json())

########NEW FILE########
__FILENAME__ = DynamoDB_Table
# Converted from DynamoDB_Table.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Output, Parameter, Ref, Template
from troposphere.dynamodb import Element, PrimaryKey, ProvisionedThroughput
from troposphere.dynamodb import Table


t = Template()

t.add_description("AWS CloudFormation Sample Template: This template "
                  "demonstrates the creation of a DynamoDB table.")

hashkeyname = t.add_parameter(Parameter(
    "HaskKeyElementName",
    Description="HashType PrimaryKey Name",
    Type="String",
    AllowedPattern="[a-zA-Z0-9]*",
    MinLength="1",
    MaxLength="2048",
    ConstraintDescription="must contain only alphanumberic characters"
))

hashkeytype = t.add_parameter(Parameter(
    "HaskKeyElementType",
    Description="HashType PrimaryKey Type",
    Type="String",
    Default="S",
    AllowedPattern="[S|N]",
    MinLength="1",
    MaxLength="1",
    ConstraintDescription="must be either S or N"
))

readunits = t.add_parameter(Parameter(
    "ReadCapacityUnits",
    Description="Provisioned read throughput",
    Type="Number",
    Default="5",
    MinValue="5",
    MaxValue="10000",
    ConstraintDescription="should be between 5 and 10000"
))

writeunits = t.add_parameter(Parameter(
    "WriteCapacityUnits",
    Description="Provisioned write throughput",
    Type="Number",
    Default="10",
    MinValue="5",
    MaxValue="10000",
    ConstraintDescription="should be between 5 and 10000"
))

myDynamoDB = t.add_resource(Table(
    "myDynamoDBTable",
    KeySchema=PrimaryKey(
        HashKeyElement=Element(Ref(hashkeyname), Ref(hashkeytype))),
    ProvisionedThroughput=ProvisionedThroughput(
        Ref(readunits), Ref(writeunits)),
))

t.add_output(Output(
    "TableName",
    Value=Ref(myDynamoDB),
    Description="Table name of the newly create DynamoDB table",
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = EC2Conditions
from __future__ import print_function

from troposphere import (
    Template, Parameter, Ref, Condition, Equals, And, Or, Not, If
)
from troposphere import ec2


parameters = {
    "One": Parameter(
        "One",
        Type="String",
    ),
    "Two": Parameter(
        "Two",
        Type="String",
    ),
    "Three": Parameter(
        "Three",
        Type="String",
    ),
    "Four": Parameter(
        "Four",
        Type="String",
    ),
    "SshKeyName": Parameter(
        "SshKeyName",
        Type="String",
    )
}

conditions = {
    "OneEqualsFoo": Equals(
        Ref("One"),
        "Foo"
    ),
    "NotOneEqualsFoo": Not(
        Condition("OneEqualsFoo")
    ),
    "BarEqualsTwo": Equals(
        "Bar",
        Ref("Two")
    ),
    "ThreeEqualsFour": Equals(
        Ref("Three"),
        Ref("Four")
    ),
    "OneEqualsFooOrBarEqualsTwo": Or(
        Condition("OneEqualsFoo"),
        Condition("BarEqualsTwo")
    ),
    "OneEqualsFooAndNotBarEqualsTwo": And(
        Condition("OneEqualsFoo"),
        Not(Condition("BarEqualsTwo"))
    ),
    "OneEqualsFooAndBarEqualsTwoAndThreeEqualsPft": And(
        Condition("OneEqualsFoo"),
        Condition("BarEqualsTwo"),
        Equals(Ref("Three"), "Pft")
    ),
    "OneIsQuzAndThreeEqualsFour": And(
        Equals(Ref("One"), "Quz"),
        Condition("ThreeEqualsFour")
    ),
    "LaunchInstance": And(
        Condition("OneEqualsFoo"),
        Condition("NotOneEqualsFoo"),
        Condition("BarEqualsTwo"),
        Condition("OneEqualsFooAndNotBarEqualsTwo"),
        Condition("OneIsQuzAndThreeEqualsFour")
    ),
    "LaunchWithGusto": And(
        Condition("LaunchInstance"),
        Equals(Ref("One"), "Gusto")
    )
}

resources = {
    "Ec2Instance": ec2.Instance(
        "Ec2Instance",
        Condition="LaunchInstance",
        ImageId=If("ConditionNameEqualsFoo", "ami-12345678", "ami-87654321"),
        InstanceType="t1.micro",
        KeyName=Ref("SshKeyName"),
        SecurityGroups=["default"],
    )
}


def template():
    t = Template()
    for p in parameters.values():
        t.add_parameter(p)
    for k in conditions:
        t.add_condition(k, conditions[k])
    for r in resources.values():
        t.add_resource(r)
    return t


print(template().to_json())

########NEW FILE########
__FILENAME__ = EC2InstanceSample
# Converted from EC2InstanceSample.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Base64, FindInMap, GetAtt
from troposphere import Parameter, Output, Ref, Template
import troposphere.ec2 as ec2


template = Template()

keyname_param = template.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH "
                "access to the instance",
    Type="String",
))

template.add_mapping('RegionMap', {
    "us-east-1": {"AMI": "ami-7f418316"},
    "us-west-1": {"AMI": "ami-951945d0"},
    "us-west-2": {"AMI": "ami-16fd7026"},
    "eu-west-1": {"AMI": "ami-24506250"},
    "sa-east-1": {"AMI": "ami-3e3be423"},
    "ap-southeast-1": {"AMI": "ami-74dda626"},
    "ap-northeast-1": {"AMI": "ami-dcfa4edd"}
})

ec2_instance = template.add_resource(ec2.Instance(
    "Ec2Instance",
    ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
    InstanceType="t1.micro",
    KeyName=Ref(keyname_param),
    SecurityGroups=["default"],
    UserData=Base64("80")
))

template.add_output([
    Output(
        "InstanceId",
        Description="InstanceId of the newly created EC2 instance",
        Value=Ref(ec2_instance),
    ),
    Output(
        "AZ",
        Description="Availability Zone of the newly created EC2 instance",
        Value=GetAtt(ec2_instance, "AvailabilityZone"),
    ),
    Output(
        "PublicIP",
        Description="Public IP address of the newly created EC2 instance",
        Value=GetAtt(ec2_instance, "PublicIp"),
    ),
    Output(
        "PrivateIP",
        Description="Private IP address of the newly created EC2 instance",
        Value=GetAtt(ec2_instance, "PrivateIp"),
    ),
    Output(
        "PublicDNS",
        Description="Public DNSName of the newly created EC2 instance",
        Value=GetAtt(ec2_instance, "PublicDnsName"),
    ),
    Output(
        "PrivateDNS",
        Description="Private DNSName of the newly created EC2 instance",
        Value=GetAtt(ec2_instance, "PrivateDnsName"),
    ),
])

print(template.to_json())

########NEW FILE########
__FILENAME__ = ElasticBeanstalk_Python_Sample
# Converted from ElasticBeanstalk_Python_Sample.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.elasticbeanstalk import Application, Environment
from troposphere.elasticbeanstalk import ApplicationVersion, OptionSettings
from troposphere.elasticbeanstalk import SourceBundle


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template ElasticBeanstalk_Python_Sample: "
    "Configure and launch the AWS Elastic Beanstalk Python sample "
    "application. **WARNING** This template creates one or more Amazon EC2 "
    "instances. You will be billed for the AWS resources used if you create "
    "a stack from this template.")

keyname = t.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH access "
                "to the AWS Elastic Beanstalk instance",
    Type="String",
))

sampleApp = t.add_resource(Application(
    "sampleApplication",
    Description="AWS Elastic Beanstalk Python Sample Application",
    ApplicationVersions=[
        ApplicationVersion(
            VersionLabel="Initial Version",
            Description="Version 1.0",
            SourceBundle=SourceBundle(
                S3Bucket=Join(
                    '-', ["elasticbeanstalk-samples", Ref("AWS::Region")]),
                S3Key="python-sample.zip"
            )
        )
    ]
))

sampleEnv = t.add_resource(Environment(
    "sampleEnvironment",
    ApplicationName=Ref(sampleApp),
    Description="AWS Elastic Beanstalk Environment running "
                "Python Sample Application",
    SolutionStackName="64bit Amazon Linux running Python",
    OptionSettings=[
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="EC2KeyName",
            Value=Ref(keyname),
        ),
    ],
    VersionLabel="Initial Version",
))

t.add_output([
    Output(
        "URL",
        Description="URL of the AWS Elastic Beanstalk Environment",
        Value=Join("", ["http://", GetAtt(sampleEnv, "EndpointURL")]),
    )
])

print(t.to_json())

########NEW FILE########
__FILENAME__ = ELBSample
# Converted from ELBSample.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Base64, FindInMap, GetAtt, GetAZs, Join, Output
from troposphere import Parameter, Ref, Template
import troposphere.ec2 as ec2
import troposphere.elasticloadbalancing as elb


def AddAMI(template):
    template.add_mapping("RegionMap", {
        "us-west-1": {"AMI": "ami-3bcc9e7e"},
    })


def main():
    template = Template()
    AddAMI(template)

    # Add the Parameters
    keyname_param = template.add_parameter(Parameter(
        "KeyName",
        Type="String",
        Default="mark",
        Description="Name of an existing EC2 KeyPair to "
                    "enable SSH access to the instance",
    ))

    template.add_parameter(Parameter(
        "InstanceType",
        Type="String",
        Description="WebServer EC2 instance type",
        Default="m1.small",
        AllowedValues=[
            "t1.micro", "m1.small", "m1.medium", "m1.large", "m1.xlarge",
            "m2.xlarge", "m2.2xlarge", "m2.4xlarge", "c1.medium", "c1.xlarge",
            "cc1.4xlarge", "cc2.8xlarge", "cg1.4xlarge"
        ],
        ConstraintDescription="must be a valid EC2 instance type.",
    ))

    webport_param = template.add_parameter(Parameter(
        "WebServerPort",
        Type="String",
        Default="8888",
        Description="TCP/IP port of the web server",
    ))

    # Define the instance security group
    instance_sg = template.add_resource(
        ec2.SecurityGroup(
            "InstanceSecurityGroup",
            GroupDescription="Enable SSH and HTTP access on the inbound port",
            SecurityGroupIngress=[
                ec2.SecurityGroupRule(
                    IpProtocol="tcp",
                    FromPort="22",
                    ToPort="22",
                    CidrIp="0.0.0.0/0",
                ),
                ec2.SecurityGroupRule(
                    IpProtocol="tcp",
                    FromPort=Ref(webport_param),
                    ToPort=Ref(webport_param),
                    CidrIp="0.0.0.0/0",
                ),
            ]
        )
    )

    # Add the web server instances
    web_instances = []
    for name in ("Ec2Instance1", "Ec2Instance2"):
        instance = template.add_resource(ec2.Instance(
            name,
            SecurityGroups=[Ref(instance_sg)],
            KeyName=Ref(keyname_param),
            InstanceType=Ref("InstanceType"),
            ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
            UserData=Base64(Ref(webport_param)),
        ))
        web_instances.append(instance)

    elasticLB = template.add_resource(elb.LoadBalancer(
        'ElasticLoadBalancer',
        AccessLoggingPolicy=elb.AccessLoggingPolicy(
            EmitInterval=5,
            Enabled=True,
            S3BucketName="logging",
            S3BucketPrefix="myELB",
        ),
        AvailabilityZones=GetAZs(""),
        ConnectionDrainingPolicy=elb.ConnectionDrainingPolicy(
            Enabled=True,
            Timeout=300,
        ),
        CrossZone=True,
        Instances=[Ref(r) for r in web_instances],
        Listeners=[
            elb.Listener(
                LoadBalancerPort="80",
                InstancePort=Ref(webport_param),
                Protocol="HTTP",
            ),
        ],
        HealthCheck=elb.HealthCheck(
            Target=Join("", ["HTTP:", Ref(webport_param), "/"]),
            HealthyThreshold="3",
            UnhealthyThreshold="5",
            Interval="30",
            Timeout="5",
        )
    ))

    template.add_output(Output(
        "URL",
        Description="URL of the sample website",
        Value=Join("", ["http://", GetAtt(elasticLB, "DNSName")])
    ))

    print(template.to_json())


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = IAM_Policies_SNS_Publish_To_SQS
# Converted from IAM_Policies_SNS_Publish_To_SQS.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Output, Ref, Template
from troposphere.sns import Subscription, Topic
from troposphere.sqs import Queue, QueuePolicy


t = Template()

t.add_description("AWS CloudFormation Sample Template: This template "
                  "demonstrates the creation of a DynamoDB table.")

sqsqueue = t.add_resource(Queue("SQSQueue"))

snstopic = t.add_resource(Topic(
    "SNSTopic",
    Subscription=[Subscription(
        Protocol="sqs",
        Endpoint=GetAtt(sqsqueue, "Arn")
    )]
))

t.add_output(Output(
    "QueueArn",
    Value=GetAtt(sqsqueue, "Arn"),
    Description="ARN of SQS Queue",
))

t.add_resource(QueuePolicy(
    "AllowSNS2SQSPolicy",
    Queues=[Ref(sqsqueue)],
    PolicyDocument={
        "Version": "2008-10-17",
        "Id": "PublicationPolicy",
        "Statement": [{
            "Sid": "Allow-SNS-SendMessage",
            "Effect": "Allow",
            "Principal": {
              "AWS": "*"
            },
            "Action": ["sqs:SendMessage"],
            "Resource": GetAtt(sqsqueue, "Arn"),
            "Condition": {
                "ArnEquals": {"aws:SourceArn": Ref(snstopic)}
            }
        }]
    }
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = IAM_Users_Groups_and_Policies
# Converted from IAM_Users_Groups_and_Policies.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Output, Ref, Template
from troposphere.iam import AccessKey, Group, LoginProfile, PolicyType
from troposphere.iam import User, UserToGroupAddition


t = Template()

t.add_description("AWS CloudFormation Sample Template: This template "
                  "demonstrates the creation of IAM User/Group.")

cfnuser = t.add_resource(User(
    "CFNUser",
    LoginProfile=LoginProfile("Password"))
)

cfnusergroup = t.add_resource(Group("CFNUserGroup"))
cfnadmingroup = t.add_resource(Group("CFNAdminGroup"))

cfnkeys = t.add_resource(AccessKey(
    "CFNKeys",
    UserName=Ref(cfnuser))
)

users = t.add_resource(UserToGroupAddition(
    "Users",
    GroupName=Ref(cfnusergroup),
    Users=Ref(cfnuser),
))

admins = t.add_resource(UserToGroupAddition(
    "Admins",
    GroupName=Ref(cfnadmingroup),
    Users=Ref(cfnuser),
))

t.add_resource(PolicyType(
    "CFNUserPolicies",
    PolicyName="CFNUsers",
    PolicyDocument={
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "cloudformation:Describe*",
                "cloudformation:List*",
                "cloudformation:Get*"
            ],
            "Resource": "*"
        }],
        "Groups": Ref(cfnadmingroup),
    }
))

t.add_output(Output(
    "AccessKey",
    Value=Ref(cfnkeys),
    Description="AWSAccessKeyId of new user",
))

t.add_output(Output(
    "SecretKey",
    Value=GetAtt(cfnkeys, "SecretAccessKey"),
    Description="AWSSecretKey of new user",
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = IAM_Users_snippet
# Converted from IAM_Users_Groups_and_Policies.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Ref, Template
from troposphere.iam import LoginProfile, Policy, User
import awacs
import awacs.aws
import awacs.sns
import awacs.sqs


t = Template()

t.add_resource(User(
    "myuser",
    Path="/",
    LoginProfile=LoginProfile("myP@ssW0rd"),
    Policies=[
        Policy(
            PolicyName="giveaccesstoqueueonly",
            PolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.aws.Action("sqs", "*")],
                        Resource=[GetAtt("myqueue", "Arn")],
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Deny,
                        Action=[awacs.aws.Action("sqs", "*")],
                        NotResource=[GetAtt("myqueue", "Arn")],
                    ),
                ],
            )
        ),
        Policy(
            PolicyName="giveaccesstotopiconly",
            PolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.aws.Action("sns", "*")],
                        Resource=[Ref("mytopic")],
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Deny,
                        Action=[awacs.aws.Action("sns", "*")],
                        NotResource=[Ref("mytopic")],
                    ),
                ],
            )
        ),
    ]
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = Kinesis_Stream
# This is an example of a Kinesis Stream

from troposphere import Output
from troposphere import Ref, Template
import troposphere.kinesis as kinesis


template = Template()

kinesis_stream = template.add_resource(kinesis.Stream(
    "TestStream",
    ShardCount=1
))

template.add_output([
    Output(
        "StreamName",
        Description="Stream Name (Physical ID)",
        Value=Ref(kinesis_stream),
    ),
])

print(template.to_json())

########NEW FILE########
__FILENAME__ = OpenStack_AutoScaling
# This is an example of an AutoScaling/ELB setup for OpenStack.
# It assumes you have a compatible LBaaS setup running.
#
# Available resources are defined at:
#   http://docs.openstack.org/developer/heat/template_guide/openstack.html
#   http://docs.openstack.org/developer/heat/template_guide/cfn.html

from troposphere import Base64, GetAZs, Join, Ref, Template
from troposphere import autoscaling
from troposphere.openstack import heat, neutron


template = Template()

# Define our health monitor
health_mon = template.add_resource(neutron.HealthMonitor(
    "MyHealthMon",
    type="HTTP",
    delay=3,
    max_retries=5,
    timeout=10,
    url_path="/",
    expected_codes="200"
))

# Define our pool and VIP
pool = template.add_resource(neutron.Pool(
    "MyPool",
    name="mypool",
    description="My instance pool",
    lb_method="ROUND_ROBIN",
    monitors=[Ref(health_mon)],
    protocol="HTTP",
    subnet_id="c5b15643-1358-4796-af8f-c9050b0b3e2a",
    vip=neutron.VIP(
        name="my-vip",
        description="My VIP",
        connection_limit=100,
        protocol_port=80
    )
))

# Define the loadbalancer
loadbalancer = template.add_resource(neutron.LoadBalancer(
    "MyLoadBalancer",
    pool_id=Ref(pool),
    protocol_port=80
))

# Define the instance security group, to allow:
#   - SSH from our trusted network
#   - HTTP from the security group used by our LBaaS
#   - ICMP from everywhere
security_group = template.add_resource(
    neutron.SecurityGroup(
        "MySecurityGroup",
        description="Instance Security Group",
        rules=[
            neutron.SecurityGroupRule(
                protocol='tcp',
                port_range_min=22,
                port_range_max=22,
                remote_ip_prefix="192.168.1.0/24",
            ),
            neutron.SecurityGroupRule(
                protocol='tcp',
                port_range_min=80,
                port_range_max=80,
                remote_mode="remote_group_id",
                remote_group_id="faf49966-ffc2-4602-84e9-917ae2ce7b89"
            ),
            neutron.SecurityGroupRule(
                protocol='icmp',
                remote_ip_prefix="0.0.0.0/0",
            ),
        ]
    )
)

# Define our launch configuration (AWS compatibility resource)
launch_config = template.add_resource(autoscaling.LaunchConfiguration(
    "MyLaunchConfig",
    KeyName="bootstrap",
    InstanceType="t1.micro",
    ImageId="Ubuntu",
    SecurityGroups=[Ref(security_group)],
    UserData=Base64(Join('\n', [
        "#!/bin/bash",
        "echo \"Upgrade started at $(date)\"",
        "apt-get update",
        "apt-get -y upgrade",
        "echo \"Upgrade complete at $(date)\"",
    ]))
))

# Define our AutoScaling Group, using the AWS compatability layer.
# It's not a native heat type, but it's a clone of the AWS type with fixes to
# work correctly on OpenStack.
# VPCZoneIdentifier here is our OpenStack subnet ID.
autoscaling_group = template.add_resource(heat.AWSAutoScalingGroup(
    "MyAutoScalingGroup",
    LaunchConfigurationName=Ref(launch_config),
    MinSize="1",
    MaxSize="2",
    DesiredCapacity="2",
    AvailabilityZones=GetAZs(""),
    VPCZoneIdentifier=["1016941e-8462-4a3a-a11d-d7836ca7a2df"],
    LoadBalancerNames=Ref(loadbalancer),
))

print(template.to_json())

########NEW FILE########
__FILENAME__ = OpenStack_Server
# This is a simple example of how to provision an OpenStack Server using Heat
# native OpenStack resources

from troposphere import Base64, Join
from troposphere import Parameter, Ref, Template
from troposphere.openstack import neutron, nova


template = Template()

keyname_param = template.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing OpenStack KeyPair to enable SSH "
                "access to the instance",
    Type="String",
))

# Define the instance security group, to allow:
#   - SSH from our trusted network
#   - ICMP from everywhere
security_group = template.add_resource(
    neutron.SecurityGroup(
        "OpenStackSecurityGroup",
        description="Instance Security Group",
        rules=[
            neutron.SecurityGroupRule(
                protocol='tcp',
                port_range_min=22,
                port_range_max=22,
                remote_ip_prefix="192.168.1.0/24",
            ),
            neutron.SecurityGroupRule(
                protocol='icmp',
                remote_ip_prefix="0.0.0.0/0",
            ),
        ]
    )
)


openstack_instance = template.add_resource(nova.Server(
    "OpenStackInstance",
    image="MyImage",
    flavor="t1.micro",
    key_name=Ref(keyname_param),
    networks=[neutron.Port(
        "OpenStackPort",
        fixed_ips=[neutron.FixedIP(
            ip_address="192.168.1.20"
        )],
        network_id="3e47c369-7007-472e-9e96-7dadb51e3e99",
        security_groups=[Ref(security_group)],
    )],
    user_data=Base64(Join('\n', [
        "#!/bin/bash",
        "echo \"Upgrade started at $(date)\"",
        "apt-get update",
        "apt-get -y upgrade",
        "echo \"Upgrade complete at $(date)\"",
    ]))
))

print(template.to_json())

########NEW FILE########
__FILENAME__ = OpsWorksSnippet
# Converted from AWS OpsWorks Snippets located at:
# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/quickref-opsworks.html

from troposphere import GetAZs, Join
from troposphere import Parameter, Ref, Template
from troposphere.elasticloadbalancing import LoadBalancer, HealthCheck
from troposphere.opsworks import App, ElasticLoadBalancerAttachment, Instance
from troposphere.opsworks import Layer, Stack
from troposphere.opsworks import Source, Recipes, VolumeConfiguration


template = Template()

template.add_version("2010-09-09")

ServiceRole = template.add_parameter(Parameter(
    "ServiceRole",
    Default="aws-opsworks-service-role",
    Description="The OpsWorks service role",
    Type="String",
    MinLength="1",
    MaxLength="64",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9-]*",
    ConstraintDescription="must begin with a letter and contain only " +
                          "alphanumeric characters.",
))

InstanceRole = template.add_parameter(Parameter(
    "InstanceRole",
    Default="aws-opsworks-ec2-role",
    Description="The OpsWorks instance role",
    Type="String",
    MinLength="1",
    MaxLength="64",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9-]*",
    ConstraintDescription="must begin with a letter and contain only " +
                          "alphanumeric characters.",
))

AppName = template.add_parameter(Parameter(
    "AppName",
    Default="myapp",
    Description="The app name",
    Type="String",
    MinLength="1",
    MaxLength="64",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription="must begin with a letter and contain only " +
                          "alphanumeric characters.",
))

MysqlRootPassword = template.add_parameter(Parameter(
    "MysqlRootPassword",
    Description="MysqlRootPassword",
    NoEcho=True,
    Type="String",
))

myStack = template.add_resource(Stack(
    "myStack",
    Name=Ref("AWS::StackName"),
    ServiceRoleArn=Join(
        "",
        [
            "arn:aws:iam::",
            Ref("AWS::AccountId"),
            ":role/", Ref(ServiceRole)
        ]),
    DefaultInstanceProfileArn=Join(
        "",
        [
            "arn:aws:iam::",
            Ref("AWS::AccountId"),
            ":instance-profile/",
            Ref(InstanceRole)
        ]),
    UseCustomCookbooks=True,
    CustomCookbooksSource=Source(
        Type="git",
        Url="git://github.com/amazonwebservices/" +
            "opsworks-example-cookbooks.git",
    ),
))

myLayer = template.add_resource(Layer(
    "myLayer",
    StackId=Ref(myStack),
    Type="php-app",
    Shortname="php-app",
    EnableAutoHealing=True,
    AutoAssignElasticIps=False,
    AutoAssignPublicIps=True,
    Name="MyPHPApp",
    CustomRecipes=Recipes(
        Configure=["phpapp::appsetup"],
    ),
))

DBLayer = template.add_resource(Layer(
    "DBLayer",
    StackId=Ref(myStack),
    Type="db-master",
    Shortname="db-layer",
    EnableAutoHealing=True,
    AutoAssignElasticIps=False,
    AutoAssignPublicIps=True,
    Name="MyMySQL",
    CustomRecipes=Recipes(
        Setup=["phpapp::dbsetup"]
    ),
    Attributes={
        "MysqlRootPassword": Ref(MysqlRootPassword),
        "MysqlRootPasswordUbiquitous": "true",
    },
    VolumeConfigurations=[
        VolumeConfiguration(
            MountPoint="/vol/mysql",
            NumberOfDisks=1,
            Size=10,
        )
    ],
))

ELB = template.add_resource(LoadBalancer(
    "ELB",
    AvailabilityZones=GetAZs(""),
    Listeners=[{
        "LoadBalancerPort": "80",
        "InstancePort": "80",
        "Protocol": "HTTP",
        "InstanceProtocol": "HTTP",
    }],
    HealthCheck=HealthCheck(
        Target="HTTP:80/",
        HealthyThreshold="2",
        UnhealthyThreshold="10",
        Interval="30",
        Timeout="5",
    ),
))

ELBAttachment = template.add_resource(ElasticLoadBalancerAttachment(
    "ELBAttachment",
    ElasticLoadBalancerName=Ref(ELB),
    LayerId=Ref(myLayer),
))

myAppInstance1 = template.add_resource(Instance(
    "myAppInstance1",
    StackId=Ref(myStack),
    LayerIds=[Ref(myLayer)],
    InstanceType="m1.small",
))

myAppInstance2 = template.add_resource(Instance(
    "myAppInstance2",
    StackId=Ref(myStack),
    LayerIds=[Ref(myLayer)],
    InstanceType="m1.small",
))

myDBInstance = template.add_resource(Instance(
    "myDBInstance",
    StackId=Ref(myStack),
    LayerIds=[Ref(DBLayer)],
    InstanceType="m1.small",
))

myApp = template.add_resource(App(
    "myApp",
    StackId=Ref(myStack),
    Type="php",
    Name=Ref(AppName),
    AppSource=Source(
        Type="git",
        Url="git://github.com/amazonwebservices/" +
            "opsworks-demo-php-simple-app.git",
        Revision="version2",
    ),
    Attributes={
        "DocumentRoot": "web",
    },
))

print(template.to_json())

########NEW FILE########
__FILENAME__ = RDS_VPC
# Converted from RDS_VPC.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Join, Output, Parameter, Ref, Template
from troposphere.ec2 import SecurityGroup
from troposphere.rds import DBInstance, DBSubnetGroup


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template VPC_RDS_DB_Instance: Sample template "
    "showing how to create an RDS DBInstance in an existing Virtual Private "
    "Cloud (VPC). **WARNING** This template creates an Amazon Relational "
    "Database Service database instance. You will be billed for the AWS "
    "resources used if you create a stack from this template.")

vpcid = t.add_parameter(Parameter(
    "VpcId",
    Type="String",
    Description="VpcId of your existing Virtual Private Cloud (VPC)"
))

subnet = t.add_parameter(Parameter(
    "Subnets",
    Type="CommaDelimitedList",
    Description=(
        "The list of SubnetIds, for at least two Availability Zones in the "
        "region in your Virtual Private Cloud (VPC)")
))

dbname = t.add_parameter(Parameter(
    "DBName",
    Default="MyDatabase",
    Description="The database name",
    Type="String",
    MinLength="1",
    MaxLength="64",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=("must begin with a letter and contain only"
                           " alphanumeric characters.")
))

dbuser = t.add_parameter(Parameter(
    "DBUser",
    NoEcho=True,
    Description="The database admin account username",
    Type="String",
    MinLength="1",
    MaxLength="16",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=("must begin with a letter and contain only"
                           " alphanumeric characters.")
))

dbpassword = t.add_parameter(Parameter(
    "DBPassword",
    NoEcho=True,
    Description="The database admin account password",
    Type="String",
    MinLength="1",
    MaxLength="41",
    AllowedPattern="[a-zA-Z0-9]*",
    ConstraintDescription="must contain only alphanumeric characters."
))

dbclass = t.add_parameter(Parameter(
    "DBClass",
    Default="db.m1.small",
    Description="Database instance class",
    Type="String",
    AllowedValues=[
        "db.m1.small", "db.m1.large", "db.m1.xlarge", "db.m2.xlarge",
        "db.m2.2xlarge", "db.m2.4xlarge"],
    ConstraintDescription="must select a valid database instance type.",
))

dballocatedstorage = t.add_parameter(Parameter(
    "DBAllocatedStorage",
    Default="5",
    Description="The size of the database (Gb)",
    Type="Number",
    MinValue="5",
    MaxValue="1024",
    ConstraintDescription="must be between 5 and 1024Gb.",
))


mydbsubnetgroup = t.add_resource(DBSubnetGroup(
    "MyDBSubnetGroup",
    DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
    SubnetIds=Ref(subnet),
))

myvpcsecuritygroup = t.add_resource(SecurityGroup(
    "myVPCSecurityGroup",
    GroupDescription="Security group for RDS DB Instance.",
    VpcId=Ref(vpcid)
))

mydb = t.add_resource(DBInstance(
    "MyDB",
    DBName=Ref(dbname),
    AllocatedStorage=Ref(dballocatedstorage),
    DBInstanceClass=Ref(dbclass),
    Engine="MySQL",
    EngineVersion="5.5",
    MasterUsername=Ref(dbuser),
    MasterUserPassword=Ref(dbpassword),
    DBSubnetGroupName=Ref(mydbsubnetgroup),
    VPCSecurityGroups=[Ref(myvpcsecuritygroup)],
))

t.add_output(Output(
    "JDBCConnectionString",
    Description="JDBC connection string for database",
    Value=Join("", [
        "jdbc:mysql://",
        GetAtt("MyDB", "Endpoint.Address"),
        GetAtt("MyDB", "Endpoint.Port"),
        "/",
        Ref(dbname)
    ])
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = RDS_with_DBParameterGroup
# Converted from RDS_with_DBParameterGroup.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Parameter, Ref, Template
from troposphere.rds import DBInstance, DBParameterGroup


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template RDS_with_DBParameterGroup: Sample "
    "template showing how to create an Amazon RDS Database Instance with "
    "a DBParameterGroup.**WARNING** This template creates an Amazon "
    "Relational Database Service database instance. You will be billed for "
    "the AWS resources used if you create a stack from this template.")

dbuser = t.add_parameter(Parameter(
    "DBUser",
    NoEcho=True,
    Description="The database admin account username",
    Type="String",
    MinLength="1",
    MaxLength="16",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=("must begin with a letter and contain only"
                           " alphanumeric characters.")
))

dbpassword = t.add_parameter(Parameter(
    "DBPassword",
    NoEcho=True,
    Description="The database admin account password",
    Type="String",
    MinLength="1",
    MaxLength="41",
    AllowedPattern="[a-zA-Z0-9]*",
    ConstraintDescription="must contain only alphanumeric characters."
))


myrdsparamgroup = t.add_resource(DBParameterGroup(
    "MyRDSParamGroup",
    Family="MySQL5.5",
    Description="CloudFormation Sample Database Parameter Group",
    Parameters={
        "autocommit": "1",
        "general_log": "1",
        "old_passwords": "0"
    }
))

mydb = t.add_resource(DBInstance(
    "MyDB",
    AllocatedStorage="5",
    DBInstanceClass="db.m1.small",
    Engine="MySQL",
    EngineVersion="5.5",
    MasterUsername=Ref(dbuser),
    MasterUserPassword=Ref(dbpassword),
    DBParameterGroupName=Ref(myrdsparamgroup),
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = Route53_A
# Converted from Route53_A.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.ec2 import Instance
from troposphere.route53 import RecordSetType


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template Route53_A: "
    "Sample template showing how to create an Amazon Route 53 A record that "
    "maps to the public IP address of an EC2 instance. It assumes that you "
    "already have a Hosted Zone registered with Amazon Route 53. **WARNING** "
    "This template creates an Amazon EC2 instance. You will be billed for "
    "the AWS resources used if you create a stack from this template.")

hostedzone = t.add_parameter(Parameter(
    "HostedZone",
    Description="The DNS name of an existing Amazon Route 53 hosted zone",
    Type="String",
))

t.add_mapping('RegionMap', {
    "us-east-1": {"AMI": "ami-7f418316"},
    "us-west-1": {"AMI": "ami-951945d0"},
    "us-west-2": {"AMI": "ami-16fd7026"},
    "eu-west-1": {"AMI": "ami-24506250"},
    "sa-east-1": {"AMI": "ami-3e3be423"},
    "ap-southeast-1": {"AMI": "ami-74dda626"},
    "ap-northeast-1": {"AMI": "ami-dcfa4edd"}
})

instance = t.add_resource(Instance(
    "Ec2Instance",
    ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
    InstanceType="m1.small",
))

myDNSRecord = t.add_resource(RecordSetType(
    "myDNSRecord",
    HostedZoneName=Join("", [Ref(hostedzone), "."]),
    Comment="DNS name for my instance.",
    Name=Join("", [Ref(instance), ".", Ref("AWS::Region"), ".",
              Ref(hostedzone), "."]),
    Type="A",
    TTL="900",
    ResourceRecords=[GetAtt("Ec2Instance", "PublicIp")],
))


t.add_output(Output("DomainName", Value=Ref(myDNSRecord)))

print(t.to_json())

########NEW FILE########
__FILENAME__ = Route53_CNAME
# Converted from Route53_CNAME.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.route53 import RecordSetType


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template Route53_CNAME: Sample template "
    "showing how to create an Amazon Route 53 CNAME record.  It assumes that "
    "you already  have a Hosted Zone registered with Amazon Route 53. "
    "**WARNING** This template creates an Amazon EC2 instance. "
    "You will be billed for the AWS resources used if you create "
    "a stack from this template.")

hostedzone = t.add_parameter(Parameter(
    "HostedZone",
    Description="The DNS name of an existing Amazon Route 53 hosted zone",
    Type="String",
))

myDNSRecord = t.add_resource(RecordSetType(
    "myDNSRecord",
    HostedZoneName=Join("", [Ref(hostedzone), "."]),
    Comment="CNAME redirect to aws.amazon.com.",
    Name=Join("", [Ref("AWS::StackName"), ".", Ref("AWS::Region"), ".",
              Ref(hostedzone), "."]),
    Type="CNAME",
    TTL="900",
    ResourceRecords=["aws.amazon.com"]
))


t.add_output(Output("DomainName", Value=Ref(myDNSRecord)))

print(t.to_json())

########NEW FILE########
__FILENAME__ = Route53_RoundRobin
# Converted from Route53_RoundRobin.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Join
from troposphere import Parameter, Ref, Template
from troposphere.route53 import RecordSet, RecordSetGroup


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template Route53_RoundRobin: Sample template "
    "showing how to use weighted round robin (WRR) DNS entried via Amazon "
    "Route 53. This contrived sample uses weighted CNAME records to "
    "illustrate that the weighting influences the return records. It assumes "
    " that you already have a Hosted Zone registered with Amazon Route 53. "
    "**WARNING** This template creates an Amazon EC2 instance. "
    "You will be billed for the AWS resources used if you create "
    "a stack from this template.")

hostedzone = t.add_parameter(Parameter(
    "HostedZone",
    Description="The DNS name of an existing Amazon Route 53 hosted zone",
    Type="String",
))

myDNSRecord = t.add_resource(RecordSetGroup(
    "myDNSRecord",
    HostedZoneName=Join("", [Ref(hostedzone), "."]),
    Comment="Contrived example to redirect to aws.amazon.com 75% of the time "
            "and www.amazon.com 25% of the time.",
    RecordSets=[
        RecordSet(
            SetIdentifier=Join(" ", [Ref("AWS::StackName"), "AWS"]),
            Name=Join("", [Ref("AWS::StackName"), ".", Ref("AWS::Region"), ".",
                      Ref(hostedzone), "."]),
            Type="CNAME",
            TTL="900",
            ResourceRecords=["aws.amazon.com"],
            Weight="3",
        ),
        RecordSet(
            SetIdentifier=Join(" ", [Ref("AWS::StackName"), "Amazon"]),
            Name=Join("", [Ref("AWS::StackName"), ".", Ref("AWS::Region"), ".",
                      Ref(hostedzone), "."]),
            Type="CNAME",
            TTL="900",
            ResourceRecords=["www.amazon.com"],
            Weight="1",
        ),
    ],
))


print(t.to_json())

########NEW FILE########
__FILENAME__ = S3_Bucket
# Converted from S3_Bucket.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Output, Ref, Template
from troposphere.s3 import Bucket, PublicRead


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template S3_Bucket: Sample template showing "
    "how to create a publicly accessible S3 bucket. "
    "**WARNING** This template creates an Amazon EC2 instance. "
    "You will be billed for the AWS resources used if you create "
    "a stack from this template.")

s3bucket = t.add_resource(Bucket("S3Bucket", AccessControl=PublicRead,))

t.add_output(Output(
    "BucketName",
    Value=Ref(s3bucket),
    Description="Name of S3 bucket to hold website content"
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = S3_Website_Bucket_With_Retain_On_Delete
# Converted from S3_Website_Bucket_With_Retain_On_Delete.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Join, Output, Template
from troposphere.s3 import Bucket, PublicRead, WebsiteConfiguration


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template "
    "S3_Website_Bucket_With_Retain_On_Delete: Sample template showing how to "
    "create a publicly accessible S3 bucket configured for website access "
    "with a deletion policy of retail on delete. "
    "**WARNING** This template creates an Amazon EC2 instance. "
    "You will be billed for the AWS resources used if you create "
    "a stack from this template.")

s3bucket = t.add_resource(Bucket(
    "S3Bucket",
    AccessControl=PublicRead,
    WebsiteConfiguration=WebsiteConfiguration(
        IndexDocument="index.html",
        ErrorDocument="error.html"
    )
))
# XXX - Add "DeletionPolicy" : "Retain" to the resource

t.add_output([
    Output(
        "WebsiteURL",
        Value=GetAtt(s3bucket, "WebsiteURL"),
        Description="URL for website hosted on S3"
    ),
    Output(
        "S3BucketSecureURL",
        Value=Join("", ["http://", GetAtt(s3bucket, "DomainName")]),
        Description="Name of S3 bucket to hold website content"
    ),
])

print(t.to_json())

########NEW FILE########
__FILENAME__ = SQSDLQ
# Converted from SQS_With_CloudWatch_Alarms.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Output, Ref, Template
from troposphere.sqs import Queue, RedrivePolicy


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template SQS: Sample template showing how to "
    "create an SQS queue with a dead letter queue. **WARNING** This template "
    "creates Amazon SQS Queues. You will be billed for the AWS resources used "
    "if you create a stack from this template.")

mysourcequeue = t.add_resource(Queue(
    "MySourceQueue",
    RedrivePolicy=RedrivePolicy(
        deadLetterTargetArn=GetAtt("MyDeadLetterQueue", "Arn"),
        maxReceiveCount="5",
    )
))

mydeadletterqueue = t.add_resource(Queue("MyDeadLetterQueue"))

t.add_output([
    Output(
        "SourceQueueURL",
        Description="URL of the source queue",
        Value=Ref(mysourcequeue)
    ),
    Output(
        "SourceQueueARN",
        Description="ARN of the source queue",
        Value=GetAtt(mysourcequeue, "Arn")
    ),
    Output(
        "DeadLetterQueueURL",
        Description="URL of the dead letter queue",
        Value=Ref(mydeadletterqueue)
    ),
    Output(
        "DeadLetterQueueARN",
        Description="ARN of the dead letter queue",
        Value=GetAtt(mydeadletterqueue, "Arn")
    ),
])

print(t.to_json())

########NEW FILE########
__FILENAME__ = SQS_With_CloudWatch_Alarms
# Converted from SQS_With_CloudWatch_Alarms.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Output, Parameter, Ref, Template
from troposphere.cloudwatch import Alarm, MetricDimension
from troposphere.sns import Subscription, Topic
from troposphere.sqs import Queue


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template SQS_With_CloudWatch_Alarms: Sample "
    "template showing how to create an SQS queue with AWS CloudWatch alarms "
    "on queue depth. **WARNING** This template creates an Amazon SQS Queue "
    "and one or more Amazon CloudWatch alarms. You will be billed for the "
    "AWS resources used if you create a stack from this template.")

alarmemail = t.add_parameter(
    Parameter(
        "AlarmEmail",
        Default="nobody@amazon.com",
        Description="Email address to notify if there are any "
                    "operational issues",
        Type="String",
    )
)

myqueue = t.add_resource(Queue("MyQueue"))

alarmtopic = t.add_resource(
    Topic(
        "AlarmTopic",
        Subscription=[
            Subscription(
                Endpoint=Ref(alarmemail),
                Protocol="email"
            ),
        ],
    )
)

queuedepthalarm = t.add_resource(
    Alarm(
        "QueueDepthAlarm",
        AlarmDescription="Alarm if queue depth grows beyond 10 messages",
        Namespace="AWS/SQS",
        MetricName="ApproximateNumberOfMessagesVisible",
        Dimensions=[
            MetricDimension(
                Name="QueueName",
                Value=GetAtt(myqueue, "QueueName")
            ),
        ],
        Statistic="Sum",
        Period="300",
        EvaluationPeriods="1",
        Threshold="10",
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[Ref(alarmtopic), ],
        InsufficientDataActions=[Ref(alarmtopic), ],
    )
)

t.add_output([
    Output(
        "QueueURL",
        Description="URL of newly created SQS Queue",
        Value=Ref(myqueue)
    ),
    Output(
        "QueueARN",
        Description="ARN of newly created SQS Queue",
        Value=GetAtt(myqueue, "Arn")
    ),
    Output(
        "QueueName",
        Description="Name newly created SQS Queue",
        Value=GetAtt(myqueue, "QueueName")
    ),
])

print(t.to_json())

########NEW FILE########
__FILENAME__ = VPC_EC2_Instance_With_Multiple_Dynamic_IPAddresses
# Converted from VPC_EC2_Instance_With_Multiple_Dynamic_IPAddresses
# template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import FindInMap, GetAtt, Join
from troposphere import Parameter, Output, Ref, Select, Tags, Template
import troposphere.ec2 as ec2


template = Template()

keyname_param = template.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH "
                "access to the instance",
    Type="String",
))

vpcid_param = template.add_parameter(Parameter(
    "VpcId",
    Description="VpcId of your existing Virtual Private Cloud (VPC)",
    Type="String",
))

subnetid_param = template.add_parameter(Parameter(
    "SubnetId",
    Description="SubnetId of an existing subnet (for the primary network) in "
                "your Virtual Private Cloud (VPC)" "access to the instance",
    Type="String",
))

secondary_ip_param = template.add_parameter(Parameter(
    "SecondaryIPAddressCount",
    Description="Number of secondary IP addresses to assign to the network "
                "interface (1-5)",
    ConstraintDescription="must be a number from 1 to 5.",
    Type="Number",
    Default="1",
    MinValue="1",
    MaxValue="5",
))

sshlocation_param = template.add_parameter(Parameter(
    "SSHLocation",
    Description="The IP address range that can be used to SSH to the "
                "EC2 instances",
    Type="String",
    MinLength="9",
    MaxLength="18",
    Default="0.0.0.0/0",
    AllowedPattern="(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})"
                   "/(\\d{1,2})",
    ConstraintDescription="must be a valid IP CIDR range of the "
                          "form x.x.x.x/x."
))

template.add_mapping('RegionMap', {
    "us-east-1": {"AMI": "ami-7f418316"},
    "us-west-1": {"AMI": "ami-951945d0"},
    "us-west-2": {"AMI": "ami-16fd7026"},
    "eu-west-1": {"AMI": "ami-24506250"},
    "sa-east-1": {"AMI": "ami-3e3be423"},
    "ap-southeast-1": {"AMI": "ami-74dda626"},
    "ap-northeast-1": {"AMI": "ami-dcfa4edd"}
})

eip1 = template.add_resource(ec2.EIP(
    "EIP1",
    Domain="vpc",
))

ssh_sg = template.add_resource(ec2.SecurityGroup(
    "SSHSecurityGroup",
    VpcId=Ref(vpcid_param),
    GroupDescription="Enable SSH access via port 22",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp=Ref(sshlocation_param),
        ),
    ],
))

eth0 = template.add_resource(ec2.NetworkInterface(
    "Eth0",
    Description="eth0",
    GroupSet=[Ref(ssh_sg), ],
    SourceDestCheck=True,
    SubnetId=Ref(subnetid_param),
    Tags=Tags(
        Name="Interface 0",
        Interface="eth0",
    ),
    SecondaryPrivateIpAddressCount=Ref(secondary_ip_param),
))

eipassoc1 = template.add_resource(ec2.EIPAssociation(
    "EIPAssoc1",
    NetworkInterfaceId=Ref(eth0),
    AllocationId=GetAtt("EIP1", "AllocationId"),
    PrivateIpAddress=GetAtt("Eth0", "PrimaryPrivateIpAddress"),
))

ec2_instance = template.add_resource(ec2.Instance(
    "EC2Instance",
    ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
    KeyName=Ref(keyname_param),
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            NetworkInterfaceId=Ref(eth0),
            DeviceIndex="0",
        ),
    ],
    Tags=Tags(Name="MyInstance",)
))

template.add_output([
    Output(
        "InstanceId",
        Description="InstanceId of the newly created EC2 instance",
        Value=Ref(ec2_instance),
    ),
    Output(
        "EIP1",
        Description="Primary public IP address for Eth0",
        Value=Join(" ", [
            "IP address", Ref(eip1), "on subnet", Ref(subnetid_param)
        ]),
    ),
    Output(
        "PrimaryPrivateIPAddress",
        Description="Primary private IP address of Eth0",
        Value=Join(" ", [
            "IP address", GetAtt("Eth0", "PrimaryPrivateIpAddress"),
            "on subnet", Ref(subnetid_param)
        ]),
    ),
    Output(
        "FirstSecondaryPrivateIPAddress",
        Description="First secondary private IP address of Eth0",
        Value=Join(" ", [
            "IP address",
            Select("0", GetAtt("Eth0", "SecondaryPrivateIpAddresses")),
            "on subnet", Ref(subnetid_param)
        ]),
    ),
])

print(template.to_json())

########NEW FILE########
__FILENAME__ = VPC_With_VPN_Connection
# Converted from VPC_With_VPN_Connection.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import Join, Output
from troposphere import Parameter, Ref, Tags, Template
from troposphere.ec2 import PortRange
from troposphere.ec2 import NetworkAcl
from troposphere.ec2 import Route
from troposphere.ec2 import VPCGatewayAttachment
from troposphere.ec2 import SubnetRouteTableAssociation
from troposphere.ec2 import Subnet
from troposphere.ec2 import CustomerGateway
from troposphere.ec2 import VPNConnectionRoute
from troposphere.ec2 import RouteTable
from troposphere.ec2 import VPC
from troposphere.ec2 import NetworkAclEntry
from troposphere.ec2 import VPNGateway
from troposphere.ec2 import SubnetNetworkAclAssociation
from troposphere.ec2 import VPNConnection


t = Template()

t.add_version("2010-09-09")

t.add_description("""\
AWS CloudFormation Sample Template VPC_With_VPN_Connection.template: \
Sample template showing how to create a private subnet with a VPN connection \
using static routing to an existing VPN endpoint. NOTE: The VPNConnection \
created will define the configuration you need yonk the tunnels to your VPN \
endpoint - you can get the VPN Gateway configuration from the AWS Management \
console. You will be billed for the AWS resources used if you create a stack \
from this template.""")
VPNAddress = t.add_parameter(Parameter(
    "VPNAddress",
    Type="String",
    Description="IP Address of your VPN device",
    MinLength="7",
    AllowedPattern="(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})",
    MaxLength="15",
    ConstraintDescription="must be a valid IP address of the form x.x.x.x",
))

OnPremiseCIDR = t.add_parameter(Parameter(
    "OnPremiseCIDR",
    ConstraintDescription=(
        "must be a valid IP CIDR range of the form x.x.x.x/x."),
    Description="IP Address range for your existing infrastructure",
    Default="10.0.0.0/16",
    MinLength="9",
    AllowedPattern="(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
    MaxLength="18",
    Type="String",
))

VPCCIDR = t.add_parameter(Parameter(
    "VPCCIDR",
    ConstraintDescription=(
        "must be a valid IP CIDR range of the form x.x.x.x/x."),
    Description="IP Address range for the VPN connected VPC",
    Default="10.1.0.0/16",
    MinLength="9",
    AllowedPattern="(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
    MaxLength="18",
    Type="String",
))

SubnetCIDR = t.add_parameter(Parameter(
    "SubnetCIDR",
    ConstraintDescription=(
        "must be a valid IP CIDR range of the form x.x.x.x/x."),
    Description="IP Address range for the VPN connected Subnet",
    Default="10.1.0.0/24",
    MinLength="9",
    AllowedPattern="(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
    MaxLength="18",
    Type="String",
))

PrivateNetworkAcl = t.add_resource(NetworkAcl(
    "PrivateNetworkAcl",
    VpcId=Ref("VPC"),
    Tags=Tags(
        Application=Ref("AWS::StackName"),
        Network="Private",
    )
))

PrivateRoute = t.add_resource(Route(
    "PrivateRoute",
    GatewayId=Ref("VPNGateway"),
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref("PrivateRouteTable"),
))

VPNGatewayAttachment = t.add_resource(VPCGatewayAttachment(
    "VPNGatewayAttachment",
    VpcId=Ref("VPC"),
    VpnGatewayId=Ref("VPNGateway"),
))

PrivateSubnetRouteTableAssociation = t.add_resource(
    SubnetRouteTableAssociation(
        "PrivateSubnetRouteTableAssociation",
        SubnetId=Ref("PrivateSubnet"),
        RouteTableId=Ref("PrivateRouteTable"),
    )
)

PrivateSubnet = t.add_resource(Subnet(
    "PrivateSubnet",
    VpcId=Ref("VPC"),
    CidrBlock=Ref(SubnetCIDR),
    Tags=Tags(
        Application=Ref("AWS::StackName"),
        Network="VPN Connected Subnet",
    )
))

CustomerGateway = t.add_resource(CustomerGateway(
    "CustomerGateway",
    BgpAsn="65000",
    IpAddress=Ref(VPNAddress),
    Type="ipsec.1",
    Tags=Tags(
        Application=Ref("AWS::StackName"),
        VPN=Join("", ["Gateway to ", Ref(VPNAddress)]),
    )
))

VPNConnectionRoute = t.add_resource(VPNConnectionRoute(
    "VPNConnectionRoute",
    VpnConnectionId=Ref("VPNConnection"),
    DestinationCidrBlock=Ref(OnPremiseCIDR),
))

PrivateRouteTable = t.add_resource(RouteTable(
    "PrivateRouteTable",
    VpcId=Ref("VPC"),
    Tags=Tags(
        Application=Ref("AWS::StackName"),
        Network="VPN Connected Subnet",
    )
))

VPC = t.add_resource(VPC(
    "VPC",
    EnableDnsSupport="true",
    CidrBlock=Ref(VPCCIDR),
    EnableDnsHostnames="true",
    Tags=Tags(
        Application=Ref("AWS::StackName"),
        Network="VPN Connected VPC",
    )
))

OutBoundPrivateNetworkAclEntry = t.add_resource(NetworkAclEntry(
    "OutBoundPrivateNetworkAclEntry",
    NetworkAclId=Ref(PrivateNetworkAcl),
    RuleNumber="100",
    Protocol="6",
    PortRange=PortRange(To="65535", From="0"),
    Egress="true",
    RuleAction="allow",
    CidrBlock="0.0.0.0/0",
))

VPNGateway = t.add_resource(VPNGateway(
    "VPNGateway",
    Type="ipsec.1",
    Tags=Tags(
        Application=Ref("AWS::StackName"),
    )
))

PrivateSubnetNetworkAclAssociation = t.add_resource(
    SubnetNetworkAclAssociation(
        "PrivateSubnetNetworkAclAssociation",
        SubnetId=Ref(PrivateSubnet),
        NetworkAclId=Ref(PrivateNetworkAcl),
    )
)

VPNConnection = t.add_resource(VPNConnection(
    "VPNConnection",
    CustomerGatewayId=Ref(CustomerGateway),
    StaticRoutesOnly="true",
    Type="ipsec.1",
    VpnGatewayId=Ref(VPNGateway),
))

InboundPrivateNetworkAclEntry = t.add_resource(NetworkAclEntry(
    "InboundPrivateNetworkAclEntry",
    NetworkAclId=Ref(PrivateNetworkAcl),
    RuleNumber="100",
    Protocol="6",
    PortRange=PortRange(To="65535", From="0"),
    Egress="false",
    RuleAction="allow",
    CidrBlock="0.0.0.0/0",
))

PrivateSubnet = t.add_output(Output(
    "PrivateSubnet",
    Description="SubnetId of the VPN connected subnet",
    Value=Ref(PrivateSubnet),
))

VPCId = t.add_output(Output(
    "VPCId",
    Description="VPCId of the newly created VPC",
    Value=Ref(VPC),
))

print(t.to_json())

########NEW FILE########
__FILENAME__ = WaitObject
# Converted from WaitObject.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import GetAtt, Output, Ref, Template
from troposphere.cloudformation import WaitCondition, WaitConditionHandle


t = Template()

t.add_description(
    "Example template showing how the WaitCondition and WaitConditionHandle "
    "are configured. With this template, the stack will not complete until "
    "either the WaitCondition timeout occurs, or you manually signal the "
    "WaitCondition object using the URL created by the WaitConditionHandle. "
    "You can use CURL or some other equivalent mechanism to signal the "
    "WaitCondition. To find the URL, use cfn-describe-stack-resources or "
    "the AWS Management Console to display the PhysicalResourceId of the "
    "WaitConditionHandle - this is the URL to use to signal. For details of "
    "the signal request see the AWS CloudFormation User Guide at "
    "http://docs.amazonwebservices.com/AWSCloudFormation/latest/UserGuide/"
)

mywaithandle = t.add_resource(WaitConditionHandle("myWaitHandle"))

mywaitcondition = t.add_resource(
    WaitCondition(
        "myWaitCondition",
        Handle=Ref(mywaithandle),
        Timeout="300",
    )
)

t.add_output([
    Output(
        "ApplicationData",
        Value=GetAtt(mywaitcondition, "Data"),
        Description="The data passed back as part of signalling the "
                    "WaitCondition"
    )
])

print(t.to_json())

########NEW FILE########
__FILENAME__ = test_basic
import json
import unittest
from troposphere import awsencode, AWSObject, Output, Parameter
from troposphere import Template, UpdatePolicy, Ref
from troposphere.ec2 import Instance, SecurityGroupRule
from troposphere.autoscaling import AutoScalingGroup
from troposphere.elasticloadbalancing import HealthCheck
from troposphere.validators import positive_integer


class TestBasic(unittest.TestCase):

    def test_badproperty(self):
        with self.assertRaises(AttributeError):
            Instance('ec2instance', foobar=True,)

    def test_badrequired(self):
        with self.assertRaises(ValueError):
            t = Template()
            t.add_resource(Instance('ec2instance'))
            t.to_json()

    def test_badtype(self):
        with self.assertRaises(AttributeError):
            Instance('ec2instance', image_id=0.11)

    def test_goodrequired(self):
        Instance('ec2instance', ImageId="ami-xxxx", InstanceType="m1.small")

    def test_extraattribute(self):

        class ExtendedInstance(Instance):
            def __init__(self, *args, **kwargs):
                self.attribute = None
                super(ExtendedInstance, self).__init__(*args, **kwargs)

        instance = ExtendedInstance('ec2instance', attribute='value')
        self.assertEqual(instance.attribute, 'value')


def call_correct(x):
    return x


def call_incorrect(x):
    raise ValueError


class FakeAWSObject(AWSObject):
    type = "Fake::AWS::Object"

    props = {
        'callcorrect': (call_correct, False),
        'callincorrect': (call_incorrect, False),
        'singlelist': (list, False),
        'multilist': ([bool, int, float], False),
        'multituple': ((bool, int), False),
        'helperfun': (positive_integer, False),
    }

    def validate(self):
        properties = self.properties
        title = self.title
        type = self.type
        if 'callcorrect' in properties and 'singlelist' in properties:
            raise ValueError(
                ("Cannot specify both 'callcorrect and 'singlelist' in "
                 "object %s (type %s)" % (title, type))
            )


class TestValidators(unittest.TestCase):

    def test_callcorrect(self):
        FakeAWSObject('fake', callcorrect=True)

    def test_callincorrect(self):
        with self.assertRaises(ValueError):
            FakeAWSObject('fake', callincorrect=True)

    def test_list(self):
        FakeAWSObject('fake', singlelist=['a', 1])

    def test_badlist(self):
        with self.assertRaises(TypeError):
            FakeAWSObject('fake', singlelist=True)

    def test_multilist(self):
        FakeAWSObject('fake', multilist=[1, True, 2, 0.3])

    def test_badmultilist(self):
        with self.assertRaises(TypeError):
            FakeAWSObject('fake', multilist=True)
        with self.assertRaises(TypeError):
            FakeAWSObject('fake', multilist=[1, 'a'])

    def test_mutualexclusion(self):
        t = Template()
        t.add_resource(FakeAWSObject(
            'fake', callcorrect=True, singlelist=[10])
        )
        with self.assertRaises(ValueError):
            t.to_json()

    def test_tuples(self):
        FakeAWSObject('fake', multituple=True)
        FakeAWSObject('fake', multituple=10)
        with self.assertRaises(TypeError):
            FakeAWSObject('fake', multituple=0.1)

    def test_helperfun(self):
        FakeAWSObject('fake', helperfun=Ref('fake_ref'))


class TestHealthCheck(unittest.TestCase):
    def test_healthy_interval_ok(self):
        HealthCheck(
            HealthyThreshold='2',
            Interval='2',
            Target='HTTP:80/index.html',
            Timeout='4',
            UnhealthyThreshold='9'
        )

    def test_healthy_interval_too_low(self):
        with self.assertRaises(ValueError):
            HealthCheck(
                HealthyThreshold='1',
                Interval='2',
                Target='HTTP:80/index.html',
                Timeout='4',
                UnhealthyThreshold='9'
            )


class TestUpdatePolicy(unittest.TestCase):

    def test_pausetime(self):
        with self.assertRaises(ValueError):
            UpdatePolicy('AutoScalingRollingUpdate', PauseTime='90')

    def test_type(self):
        with self.assertRaises(ValueError):
            UpdatePolicy('MyCoolPolicy')

    def test_works(self):
        policy = UpdatePolicy(
            'AutoScalingRollingUpdate',
            PauseTime='PT1M5S',
            MinInstancesInService='2',
            MaxBatchSize='1',
        )
        self.assertEqual(policy.PauseTime, 'PT1M5S')

    def test_mininstances(self):
        group = AutoScalingGroup(
            'mygroup',
            LaunchConfigurationName="I'm a test",
            MaxSize="1",
            MinSize="1",
            UpdatePolicy=UpdatePolicy(
                'AutoScalingRollingUpdate',
                PauseTime='PT1M5S',
                MinInstancesInService='1',
                MaxBatchSize='1',
            )
        )
        with self.assertRaises(ValueError):
            self.assertTrue(group.validate())

    def test_working(self):
        group = AutoScalingGroup(
            'mygroup',
            LaunchConfigurationName="I'm a test",
            MaxSize="4",
            MinSize="2",
            UpdatePolicy=UpdatePolicy(
                'AutoScalingRollingUpdate',
                PauseTime='PT1M5S',
                MinInstancesInService='2',
                MaxBatchSize='1',
            )
        )
        self.assertTrue(group.validate())

    def test_updatepolicy_noproperty(self):
        t = UpdatePolicy('AutoScalingRollingUpdate', PauseTime='PT1M0S')
        d = json.loads(json.dumps(t, cls=awsencode))
        with self.assertRaises(KeyError):
            d['Properties']

    def test_updatepolicy_dictname(self):
        t = UpdatePolicy('AutoScalingRollingUpdate', PauseTime='PT1M0S')
        d = json.loads(json.dumps(t, cls=awsencode))
        self.assertIn('AutoScalingRollingUpdate', d)


class TestOutput(unittest.TestCase):

    def test_noproperty(self):
        t = Output("MyOutput", Value="myvalue")
        d = json.loads(json.dumps(t, cls=awsencode))
        with self.assertRaises(KeyError):
            d['Properties']


class TestParameter(unittest.TestCase):

    def test_noproperty(self):
        t = Parameter("MyParameter", Type="String")
        d = json.loads(json.dumps(t, cls=awsencode))
        with self.assertRaises(KeyError):
            d['Properties']


class TestProperty(unittest.TestCase):

    def test_noproperty(self):
        t = SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="0.0.0.0/0",
        )
        d = json.loads(json.dumps(t, cls=awsencode))
        with self.assertRaises(KeyError):
            d['Properties']


class TestDuplicate(unittest.TestCase):

    def test_output(self):
        t = Template()
        o = Output("MyOutput", Value="myvalue")
        t.add_output(o)
        with self.assertRaises(ValueError):
            t.add_output(o)

    def test_parameter(self):
        t = Template()
        p = Parameter("MyParameter", Type="String")
        t.add_parameter(p)
        with self.assertRaises(ValueError):
            t.add_parameter(p)

    def test_resource(self):
        t = Template()
        r = FakeAWSObject('fake', callcorrect=True)
        t.add_resource(r)
        with self.assertRaises(ValueError):
            t.add_resource(r)


class TestRef(unittest.TestCase):

    def test_ref(self):
        param = Parameter("param", Description="description", Type="String")
        t = Ref(param)
        ref = json.loads(json.dumps(t, cls=awsencode))
        self.assertEqual(ref['Ref'], 'param')


class TestName(unittest.TestCase):

    def test_ref(self):
        name = 'fake'
        t = Template()
        resource = t.add_resource(Instance(name))
        self.assertEqual(resource.name, name)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_examples
import os
import re
import sys
import unittest

try:
    import StringIO as io
except ImportError:
    import io

try:
    u = unicode
except NameError:
    u = str


class TestExamples(unittest.TestCase):
    maxDiff = None

    # those are set by create_test_class
    filename = None
    expected_output = None

    def test_example(self):
        saved = sys.stdout
        stdout = io.StringIO()
        try:
            sys.stdout = stdout
            with open(self.filename) as f:
                code = compile(f.read(), self.filename, 'exec')
                exec(code, {'__name__': '__main__'})
        finally:
            sys.stdout = saved
        # rewind fake stdout so we can read it
        stdout.seek(0)
        actual_output = stdout.read()
        self.assertEqual(u(self.expected_output), u(actual_output))


def create_test_class(testname, **kwargs):
    klass = type(testname, (TestExamples,), kwargs)
    return klass


def load_tests(loader, tests, pattern):
    # Filter out all *.py files from the examples directory
    examples = 'examples'
    regex = re.compile(r'.py$', re.I)
    example_filesnames = filter(regex.search, os.listdir(examples))

    suite = unittest.TestSuite()

    for f in example_filesnames:
        testname = 'test_' + f[:-3]
        expected_output = open('tests/examples_output/%s.template' %
                               f[:-3]).read()
        test_class = create_test_class(testname, filename=examples + '/' + f,
                                       expected_output=expected_output)
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    return suite

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_validators
import unittest
from troposphere import Parameter, Ref
from troposphere.validators import boolean, integer, integer_range
from troposphere.validators import positive_integer, network_port


class TestValidators(unittest.TestCase):

    def test_boolean(self):
        for x in [True, "True", "true", 1, "1"]:
            self.assertEqual(boolean(x), "true", repr(x))
        for x in [False, "False", "false", 0, "0"]:
            self.assertEqual(boolean(x), "false", repr(x))
        for x in ["000", "111", "abc"]:
            with self.assertRaises(ValueError):
                boolean(x)

    def test_integer(self):
        self.assertEqual(integer(-1), -1)
        self.assertEqual(integer("-1"), "-1")
        self.assertEqual(integer(0), 0)
        self.assertEqual(integer("0"), "0")
        self.assertEqual(integer(65535), 65535)
        self.assertEqual(integer("65535"), "65535")
        self.assertEqual(integer(1.0), 1.0)
        with self.assertRaises(ValueError):
            integer("string")
        with self.assertRaises(ValueError):
            integer(object)
        with self.assertRaises(ValueError):
            integer(None)

    def test_positive_integer(self):
        for x in [0, 1, 65535]:
            positive_integer(x)
        for x in [-1, -10]:
            with self.assertRaises(ValueError):
                positive_integer(x)

    def test_integer_range(self):
        between_ten_and_twenty = integer_range(10, 20)
        self.assertEqual(between_ten_and_twenty(10), 10)
        self.assertEqual(between_ten_and_twenty(15), 15)
        self.assertEqual(between_ten_and_twenty(20), 20)
        for i in (-1, 9, 21, 1111111):
            with self.assertRaises(ValueError):
                between_ten_and_twenty(i)

    def test_network_port(self):
        for x in [-1, 0, 1, 1024, 65535]:
            network_port(x)
        for x in [-2, -10, 65536, 100000]:
            with self.assertRaises(ValueError):
                network_port(x)

    def test_network_port_ref(self):
        p = Parameter('myport')
        network_port(Ref(p))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = autoscaling
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty
from .validators import boolean, integer, positive_integer


EC2_INSTANCE_LAUNCH = "autoscaling:EC2_INSTANCE_LAUNCH"
EC2_INSTANCE_LAUNCH_ERROR = "autoscaling:EC2_INSTANCE_LAUNCH_ERROR"
EC2_INSTANCE_TERMINATE = "autoscaling:EC2_INSTANCE_TERMINATE"
EC2_INSTANCE_TERMINATE_ERROR = "autoscaling:EC2_INSTANCE_TERMINATE_ERROR"
TEST_NOTIFICATION = "autoscaling:TEST_NOTIFICATION"


class Tag(AWSHelperFn):
    def __init__(self, key, value, propogate):
        self.data = {
            'Key': key,
            'Value': value,
            'PropagateAtLaunch': propogate,
        }

    def JSONrepr(self):
        return self.data


class NotificationConfiguration(AWSProperty):
    props = {
        'TopicARN': (basestring, True),
        'NotificationTypes': (list, True),
    }


class MetricsCollection(AWSProperty):
    props = {
        'Granularity': (basestring, True),
        'Metrics': (list, False),
    }


class AutoScalingGroup(AWSObject):
    type = "AWS::AutoScaling::AutoScalingGroup"

    props = {
        'AvailabilityZones': (list, True),
        'Cooldown': (integer, False),
        'DesiredCapacity': (integer, False),
        'HealthCheckGracePeriod': (int, False),
        'HealthCheckType': (basestring, False),
        'InstanceId': (basestring, False),
        'LaunchConfigurationName': (basestring, True),
        'LoadBalancerNames': (list, False),
        'MaxSize': (positive_integer, True),
        'MetricsCollection': ([MetricsCollection], False),
        'MinSize': (positive_integer, True),
        'NotificationConfiguration': (NotificationConfiguration, False),
        'Tags': (list, False),  # Although docs say these are required
        'VPCZoneIdentifier': (list, False),
    }

    def validate(self):
        if 'UpdatePolicy' in self.resource:
            update_policy = self.resource['UpdatePolicy']
            if int(update_policy.MinInstancesInService) >= int(self.MaxSize):
                raise ValueError(
                    "The UpdatePolicy attribute "
                    "MinInstancesInService must be less than the "
                    "autoscaling group's MaxSize")
        return True


class LaunchConfiguration(AWSObject):
    type = "AWS::AutoScaling::LaunchConfiguration"

    props = {
        'AssociatePublicIpAddress': (boolean, False),
        'BlockDeviceMappings': (list, False),
        'EbsOptimized': (boolean, False),
        'IamInstanceProfile': (basestring, False),
        'ImageId': (basestring, True),
        'InstanceId': (basestring, False),
        'InstanceMonitoring': (boolean, False),
        'InstanceType': (basestring, True),
        'KernelId': (basestring, False),
        'KeyName': (basestring, False),
        'RamDiskId': (basestring, False),
        'SecurityGroups': (list, False),
        'SpotPrice': (basestring, False),
        'UserData': (basestring, False),
    }


class ScalingPolicy(AWSObject):
    type = "AWS::AutoScaling::ScalingPolicy"

    props = {
        'AdjustmentType': (basestring, True),
        'AutoScalingGroupName': (basestring, True),
        'Cooldown': (integer, False),
        'ScalingAdjustment': (basestring, True),
    }


class ScheduledAction(AWSObject):
    type = "AWS::AutoScaling::ScheduledAction"

    props = {
        'AutoScalingGroupName': (basestring, True),
        'DesiredCapacity': (integer, False),
        'EndTime': (basestring, True),
        'MaxSize': (integer, False),
        'MinSize': (integer, False),
        'Recurrence': (basestring, True),
        'StartTime': (basestring, True),
    }


class Trigger(AWSObject):
    type = "AWS::AutoScaling::Trigger"

    props = {
        'AutoScalingGroupName': (basestring, True),
        'BreachDuration': (integer, True),
        'Dimensions': (list, True),
        'LowerBreachScaleIncrement': (integer, False),
        'LowerThreshold': (integer, True),
        'MetricName': (basestring, True),
        'Namespace': (basestring, True),
        'Period': (integer, True),
        'Statistic': (basestring, True),
        'Unit': (basestring, False),
        'UpperBreachScaleIncrement': (integer, False),
        'UpperThreshold': (integer, True),
    }


class EBSBlockDevice(AWSProperty):
    props = {
        'SnapshotId': (basestring, False),
        'VolumeSize': (integer, False),
    }


class BlockDeviceMapping(AWSProperty):
    props = {
        'DeviceName': (basestring, True),
        'Ebs': (EBSBlockDevice, False),
        'VirtualName': (basestring, False),
    }

########NEW FILE########
__FILENAME__ = cloudformation
# Copyright (c) 2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, Ref
from .validators import integer


class Stack(AWSObject):
    type = "AWS::CloudFormation::Stack"

    props = {
        'TemplateURL': (basestring, True),
        'TimeoutInMinutes': (integer, False),
        'Parameters': (dict, False),
    }


class WaitCondition(AWSObject):
    type = "AWS::CloudFormation::WaitCondition"

    props = {
        'Count': (integer, False),
        'Handle': (Ref, True),
        'Timeout': (integer, True),
    }


class WaitConditionHandle(AWSObject):
    type = "AWS::CloudFormation::WaitConditionHandle"

    props = {}

########NEW FILE########
__FILENAME__ = cloudfront
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty
from .validators import boolean, integer, network_port


class ForwardedValues(AWSHelperFn):
    def __init__(self, querystring):
        self.data = {
            'QueryString': boolean(querystring),
        }

    def JSONrepr(self):
        return self.data


class DefaultCacheBehavior(AWSProperty):
    props = {
        'TargetOriginId': (basestring, True),
        'ForwardedValues': (ForwardedValues, False),
        'TrustedSigners': (list, False),
        'ViewerProtocolPolicy': (basestring, True),
        'MinTTL': (integer, False),
    }


class S3Origin(AWSHelperFn):
    def __init__(self, originaccessidentity):
        if not isinstance(originaccessidentity, basestring):
            raise TypeError
        self.data = {
            'OriginAccessIdentity': originaccessidentity,
        }

    def JSONrepr(self):
        return self.data


class CustomOrigin(AWSProperty):
    props = {
        'HTTPPort': (network_port, False),
        'HTTPSPort': (network_port, False),
        'OriginProtocolPolicy': (basestring, True),
    }


class Origin(AWSProperty):
    props = {
        'DomainName': (basestring, True),
        'Id': (basestring, True),
        'S3OriginConfig': (S3Origin, False),
        'CustomOriginConfig': (CustomOrigin, False),
    }


class Logging(AWSProperty):
    props = {
        'Bucket': (basestring, True),
        'Prefix': (basestring, False),
    }


class DistributionConfig(AWSProperty):
    props = {
        'Aliases': (list, False),
        'CacheBehaviors': (list, False),
        'Comment': (basestring, False),
        'DefaultCacheBehavior': (DefaultCacheBehavior, True),
        'DefaultRootObject': (basestring, False),
        'Enabled': (boolean, True),
        'Logging': (Logging, False),
        'Origins': (list, True),
    }


class Distribution(AWSObject):
    type = "AWS::CloudFront::Distribution"

    props = {
        'DistributionConfig': (DistributionConfig, True),
    }

########NEW FILE########
__FILENAME__ = cloudwatch
# Copyright (c) 2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty
from .validators import integer


class Alarm(AWSObject):
    type = "AWS::CloudWatch::Alarm"

    props = {
        'ActionsEnabled': (basestring, False),
        'AlarmActions': (list, False),
        'AlarmDescription': (basestring, False),
        'AlarmName': (basestring, False),
        'ComparisonOperator': (basestring, True),
        'Dimensions': (list, False),
        'EvaluationPeriods': (integer, True),
        'InsufficientDataActions': (list, False),
        'MetricName': (basestring, True),
        'Namespace': (basestring, True),
        'OKActions': (list, False),
        'Period': (integer, True),
        'Statistic': (basestring, True),
        'Threshold': (integer, True),
        'Unit': (basestring, False),
    }


class MetricDimension(AWSProperty):
    props = {
        'Name': (basestring, True),
        'Value': (basestring, True),
    }

########NEW FILE########
__FILENAME__ = dynamodb
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty


class Element(AWSHelperFn):
    def __init__(self, name, type):
        self.data = {
            'AttributeName': name,
            'AttributeType': type,
        }

    def JSONrepr(self):
        return self.data


class PrimaryKey(AWSProperty):
    props = {
        'HashKeyElement': (Element, True),
        'RangeKeyElement': (Element, False),
    }


class ProvisionedThroughput(AWSHelperFn):
    def __init__(self, ReadCapacityUnits, WriteCapacityUnits):
        self.data = {
            'ReadCapacityUnits': ReadCapacityUnits,
            'WriteCapacityUnits': WriteCapacityUnits,
        }

    def JSONrepr(self):
        return self.data


class Table(AWSObject):
    type = "AWS::DynamoDB::Table"

    props = {
        'KeySchema': (PrimaryKey, True),
        'ProvisionedThroughput': (ProvisionedThroughput, True),
        'TableName': (basestring, False),
    }

########NEW FILE########
__FILENAME__ = ec2
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty, Ref
from .validators import boolean, integer, integer_range, network_port


class Tag(AWSHelperFn):
    def __init__(self, key, value):
        self.data = {'Key': key, 'Value': value}

    def JSONrepr(self):
        return self.data


class CustomerGateway(AWSObject):
    type = "AWS::EC2::CustomerGateway"

    props = {
        'BgpAsn': (integer, True),
        'IpAddress': (basestring, True),
        'Tags': (list, False),
        'Type': (basestring, True),
    }


class DHCPOptions(AWSObject):
    type = "AWS::EC2::DHCPOptions"

    props = {
        'DomainName': (basestring, False),
        'DomainNameServers': (list, False),
        'NetbiosNameServers': (list, False),
        'NetbiosNodeType': (int, False),
        'NtpServers': (list, False),
        'Tags': (list, False),
    }


class EIP(AWSObject):
    type = "AWS::EC2::EIP"

    props = {
        'InstanceId': (basestring, False),
        'Domain': (basestring, False),
    }


class EIPAssociation(AWSObject):
    type = "AWS::EC2::EIPAssociation"

    props = {
        'AllocationId': (basestring, False),
        'EIP': (basestring, False),
        'InstanceId': (basestring, False),
        'NetworkInterfaceId': (basestring, False),
        'PrivateIpAddress': (basestring, False),
    }


class EBSBlockDevice(AWSProperty):
    props = {
        'DeleteOnTermination': (boolean, False),
        'Iops': (int, False),  # Conditional
        'SnapshotId': (basestring, False),  # Conditional
        'VolumeSize': (integer, False),  # Conditional
        'VolumeType': (basestring, False),
    }


class BlockDeviceMapping(AWSProperty):
    props = {
        'DeviceName': (basestring, True),
        'Ebs': (EBSBlockDevice, False),      # Conditional
        'NoDevice': (dict, False),
        'VirtualName': (basestring, False),  # Conditional
    }


class MountPoint(AWSProperty):
    props = {
        'Device': (basestring, True),
        'VolumeId': (basestring, True),
    }


class PrivateIpAddressSpecification(AWSProperty):
    props = {
        'Primary': (boolean, True),
        'PrivateIpAddress': (basestring, True),
    }


class NetworkInterfaceProperty(AWSProperty):
    props = {
        'AssociatePublicIpAddress': (boolean, False),
        'DeleteOnTermination': (boolean, False),
        'Description': (basestring, False),
        'DeviceIndex': (basestring, True),
        'GroupSet': ([basestring, Ref], False),
        'NetworkInterfaceId': (basestring, False),
        'PrivateIpAddress': (basestring, False),
        'PrivateIpAddresses': ([PrivateIpAddressSpecification], False),
        'SecondaryPrivateIpAddressCount': (int, False),
        'SubnetId': (basestring, False),
    }


class Instance(AWSObject):
    type = "AWS::EC2::Instance"

    props = {
        'AvailabilityZone': (basestring, False),
        'BlockDeviceMappings': (list, False),
        'DisableApiTermination': (boolean, False),
        'EbsOptimized': (boolean, False),
        'IamInstanceProfile': (basestring, False),
        'ImageId': (basestring, True),
        'InstanceType': (basestring, False),
        'KernelId': (basestring, False),
        'KeyName': (basestring, False),
        'Monitoring': (boolean, False),
        'NetworkInterfaces': ([NetworkInterfaceProperty], False),
        'PlacementGroupName': (basestring, False),
        'PrivateIpAddress': (basestring, False),
        'RamdiskId': (basestring, False),
        'SecurityGroupIds': (list, False),
        'SecurityGroups': (list, False),
        'SourceDestCheck': (boolean, False),
        'SubnetId': (basestring, False),
        'Tags': (list, False),
        'Tenancy': (basestring, False),
        'UserData': (basestring, False),
        'Volumes': (list, False),
    }


class InternetGateway(AWSObject):
    type = "AWS::EC2::InternetGateway"

    props = {
        'Tags': (list, False),
    }


class NetworkAcl(AWSObject):
    type = "AWS::EC2::NetworkAcl"

    props = {
        'Tags': (list, False),
        'VpcId': (basestring, True),
    }


class ICMP(AWSProperty):
    props = {
        'Code': (int, False),
        'Type': (int, False),
    }


class PortRange(AWSProperty):
    props = {
        'From': (network_port, False),
        'To': (network_port, False),
    }


class NetworkAclEntry(AWSObject):
    type = "AWS::EC2::NetworkAclEntry"

    props = {
        'CidrBlock': (basestring, True),
        'Egress': (boolean, True),
        'Icmp': (ICMP, False),  # Conditional
        'NetworkAclId': (basestring, True),
        'PortRange': (PortRange, False),  # Conditional
        'Protocol': (network_port, True),
        'RuleAction': (basestring, True),
        'RuleNumber': (integer_range(1, 32766), True),
    }


class NetworkInterface(AWSObject):
    type = "AWS::EC2::NetworkInterface"

    props = {
        'Description': (basestring, False),
        'GroupSet': (list, False),
        'PrivateIpAddress': (basestring, False),
        'PrivateIpAddresses': ([PrivateIpAddressSpecification], False),
        'SecondaryPrivateIpAddressCount': (int, False),
        'SourceDestCheck': (boolean, False),
        'SubnetId': (basestring, True),
        'Tags': (list, False),
    }


class NetworkInterfaceAttachment(AWSObject):
    type = "AWS::EC2::NetworkInterfaceAttachment"

    props = {
        'DeleteOnTermination': (boolean, False),
        'DeviceIndex': (basestring, True),
        'InstanceId': (basestring, True),
        'NetworkInterfaceId': (basestring, True),
    }


class Route(AWSObject):
    type = "AWS::EC2::Route"

    props = {
        'DestinationCidrBlock': (basestring, True),
        'GatewayId': (basestring, False),
        'InstanceId': (basestring, False),
        'NetworkInterfaceId': (basestring, False),
        'RouteTableId': (basestring, True),
    }


class RouteTable(AWSObject):
    type = "AWS::EC2::RouteTable"

    props = {
        'Tags': (list, False),
        'VpcId': (basestring, True),
    }


class SecurityGroupEgress(AWSObject):
    type = "AWS::EC2::SecurityGroupEgress"

    props = {
        'CidrIp': (basestring, False),
        'DestinationSecurityGroupId': (basestring, False),
        'FromPort': (network_port, True),
        'GroupId': (basestring, False),
        'IpProtocol': (basestring, True),
        'ToPort': (network_port, True),
        #
        # Workaround for a bug in CloudFormation and EC2 where the
        # DestinationSecurityGroupId property is ignored causing
        # egress rules targeting a security group to be ignored.
        # Using SourceSecurityGroupId instead works fine even in
        # egress rules. AWS have known about this bug for a while.
        #
        'SourceSecurityGroupId': (basestring, False),
    }


class SecurityGroupIngress(AWSObject):
    type = "AWS::EC2::SecurityGroupIngress"

    props = {
        'CidrIp': (basestring, False),
        'FromPort': (network_port, False),
        'GroupName': (basestring, False),
        'GroupId': (basestring, False),
        'IpProtocol': (basestring, True),
        'SourceSecurityGroupName': (basestring, False),
        'SourceSecurityGroupId': (basestring, False),
        'SourceSecurityGroupOwnerId': (basestring, False),
        'ToPort': (network_port, False),
    }


class SecurityGroupRule(AWSProperty):
    props = {
        'CidrIp': (basestring, False),
        'FromPort': (network_port, True),
        'IpProtocol': (basestring, True),
        'SourceSecurityGroupId': (basestring, False),
        'SourceSecurityGroupName': (basestring, False),
        'SourceSecurityGroupOwnerId': (basestring, False),
        'ToPort': (network_port, True),
    }


class SecurityGroup(AWSObject):
    type = "AWS::EC2::SecurityGroup"

    props = {
        'GroupDescription': (basestring, True),
        'SecurityGroupEgress': (list, False),
        'SecurityGroupIngress': (list, False),
        'VpcId': (basestring, False),
        'Tags': (list, False),
    }


class Subnet(AWSObject):
    type = "AWS::EC2::Subnet"

    props = {
        'AvailabilityZone': (basestring, False),
        'CidrBlock': (basestring, True),
        'Tags': (list, False),
        'VpcId': (basestring, True),
    }


class SubnetNetworkAclAssociation(AWSObject):
    type = "AWS::EC2::SubnetNetworkAclAssociation"

    props = {
        'SubnetId': (basestring, True),
        'NetworkAclId': (basestring, True),
    }


class SubnetRouteTableAssociation(AWSObject):
    type = "AWS::EC2::SubnetRouteTableAssociation"

    props = {
        'RouteTableId': (basestring, True),
        'SubnetId': (basestring, True),
    }


class Volume(AWSObject):
    type = "AWS::EC2::Volume"

    props = {
        'AvailabilityZone': (basestring, True),
        'Iops': (int, False),
        'Size': (basestring, False),
        'SnapshotId': (basestring, False),
        'Tags': (list, False),
        'VolumeType': (basestring, False),
    }


class VolumeAttachment(AWSObject):
    type = "AWS::EC2::VolumeAttachment"

    props = {
        'Device': (basestring, True),
        'InstanceId': (basestring, True),
        'VolumeId': (basestring, True),
    }


class VPC(AWSObject):
    type = "AWS::EC2::VPC"

    props = {
        'CidrBlock': (basestring, True),
        'EnableDnsSupport': (boolean, False),
        'EnableDnsHostnames': (boolean, False),
        'InstanceTenancy': (basestring, False),
        'Tags': (list, False),
    }


class VPCDHCPOptionsAssociation(AWSObject):
    type = "AWS::EC2::VPCDHCPOptionsAssociation"

    props = {
        'DhcpOptionsId': (basestring, True),
        'VpcId': (basestring, True),
    }


class VPCGatewayAttachment(AWSObject):
    type = "AWS::EC2::VPCGatewayAttachment"

    props = {
        'InternetGatewayId': (basestring, False),
        'VpcId': (basestring, True),
        'VpnGatewayId': (basestring, False),
    }


class VPNConnection(AWSObject):
    type = "AWS::EC2::VPNConnection"

    props = {
        'Type': (basestring, True),
        'CustomerGatewayId': (basestring, True),
        'StaticRoutesOnly': (boolean, False),
        'Tags': (list, False),
        'VpnGatewayId': (basestring, True),
    }


class VPNConnectionRoute(AWSObject):
    type = "AWS::EC2::VPNConnectionRoute"

    props = {
        'DestinationCidrBlock': (basestring, True),
        'VpnConnectionId': (basestring, True),
    }


class VPNGateway(AWSObject):
    type = "AWS::EC2::VPNGateway"

    props = {
        'Type': (basestring, True),
        'Tags': (list, False),
    }


class VPNGatewayRoutePropagation(AWSObject):
    type = "AWS::EC2::VPNGatewayRoutePropagation"

    props = {
        'RouteTableIds': ([basestring, Ref], False),
        'VpnGatewayId': (basestring, True),
    }

########NEW FILE########
__FILENAME__ = elasticache
# Copyright (c) 2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, Ref
from .validators import boolean, integer


class CacheCluster(AWSObject):
    type = "AWS::ElastiCache::CacheCluster"

    props = {
        'AutoMinorVersionUpgrade': (boolean, False),
        'CacheNodeType': (basestring, True),
        'CacheParameterGroupName': (basestring, False),
        'CacheSecurityGroupNames': ([basestring, Ref], False),
        'CacheSubnetGroupName': (basestring, False),
        'ClusterName': (basestring, False),
        'Engine': (basestring, True),
        'EngineVersion': (basestring, False),
        'NotificationTopicArn': (basestring, False),
        'NumCacheNodes': (integer, False),
        'Port': (int, False),
        'PreferredAvailabilityZone': (basestring, False),
        'PreferredMaintenanceWindow': (basestring, False),
        'SnapshotArns': ([basestring, Ref], False),
        'VpcSecurityGroupIds': ([basestring, Ref], False),
    }


class ParameterGroup(AWSObject):
    type = "AWS::ElastiCache::ParameterGroup"

    props = {
        'CacheParameterGroupFamily': (basestring, True),
        'Description': (basestring, True),
        'Properties': (dict, True),
    }


class SecurityGroup(AWSObject):
    type = "AWS::ElastiCache::SecurityGroup"

    props = {
        'Description': (basestring, True),
    }


class SecurityGroupIngress(AWSObject):
    type = "AWS::ElastiCache::SecurityGroupIngress"

    props = {
        'CacheSecurityGroupName': (basestring, True),
        'EC2SecurityGroupName': (basestring, True),
        'EC2SecurityGroupOwnerId': (basestring, False),
    }


class SubnetGroup(AWSObject):
    type = "AWS::ElastiCache::SubnetGroup"

    props = {
        'Description': (basestring, True),
        'SubnetIds': (list, True),
    }

########NEW FILE########
__FILENAME__ = elasticbeanstalk
# Copyright (c) 2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty


WebServer = "WebServer"
Worker = "Worker"
WebServerType = "Standard"
WorkerType = "SQS/HTTP"


class SourceBundle(AWSProperty):
    props = {
        'S3Bucket': (basestring, True),
        'S3Key': (basestring, True),
    }


class ApplicationVersion(AWSProperty):
    props = {
        'Description': (basestring, False),
        'SourceBundle': (SourceBundle, False),
        'VersionLabel': (basestring, True),
    }


class OptionSettings(AWSProperty):
    props = {
        'Namespace': (basestring, True),
        'OptionName': (basestring, True),
        'Value': (basestring, True),
    }


class ConfigurationTemplate(AWSProperty):
    props = {
        'TemplateName': (basestring, True),
        'Description': (basestring, False),
        'OptionSettings': (list, False),
        'SolutionStackName': (basestring, False),
    }


class Application(AWSObject):
    type = "AWS::ElasticBeanstalk::Application"

    props = {
        'ApplicationName': (basestring, False),
        'ApplicationVersions': (list, True),
        'ConfigurationTemplates': (list, False),
        'Description': (basestring, False),
    }


def validate_tier_name(name):
    valid_names = [WebServer, Worker]
    if name not in valid_names:
        raise ValueError('Tier name needs to be one of %r' % valid_names)
    return name


def validate_tier_type(tier_type):
    valid_types = [WebServerType, WorkerType]
    if tier_type not in valid_types:
        raise ValueError('Tier type needs to be one of %r' % valid_types)
    return tier_type


class Tier(AWSProperty):
    props = {
        'Name': (validate_tier_name, False),
        'Type': (validate_tier_type, False),
        'Version': (basestring, False),
    }


class Environment(AWSObject):
    type = "AWS::ElasticBeanstalk::Environment"

    props = {
        'ApplicationName': (basestring, True),
        'CNAMEPrefix': (basestring, False),
        'Description': (basestring, False),
        'EnvironmentName': (basestring, False),
        'OptionSettings': (list, False),
        'OptionsToRemove': (list, False),
        'SolutionStackName': (basestring, False),
        'TemplateName': (basestring, False),
        'Tier': (Tier, False),
        'VersionLabel': (basestring, False),
    }

########NEW FILE########
__FILENAME__ = elasticloadbalancing
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty
from .validators import boolean, integer_range, positive_integer, network_port


class AppCookieStickinessPolicy(AWSProperty):
    props = {
        'CookieName': (basestring, True),
        'PolicyName': (basestring, True),
    }


class HealthCheck(AWSProperty):
    props = {
        'HealthyThreshold': (integer_range(2, 10), True),
        'Interval': (positive_integer, True),
        'Target': (basestring, True),
        'Timeout': (positive_integer, True),
        'UnhealthyThreshold': (integer_range(2, 10), True),
    }


class LBCookieStickinessPolicy(AWSProperty):
    props = {
        'CookieExpirationPeriod': (basestring, False),
        'PolicyName': (basestring, False),
    }


class Listener(AWSProperty):
    props = {
        'InstancePort': (network_port, True),
        'InstanceProtocol': (basestring, False),
        'LoadBalancerPort': (network_port, True),
        'PolicyNames': (list, False),
        'Protocol': (basestring, True),
        'SSLCertificateId': (basestring, False),
    }


class Policy(AWSProperty):
    props = {
        'Attributes': ([dict], False),
        'InstancePorts': (list, False),
        'LoadBalancerPorts': (list, False),
        'PolicyName': (basestring, True),
        'PolicyType': (basestring, True),
    }


class ConnectionDrainingPolicy(AWSProperty):
    props = {
        'Enabled': (bool, True),
        'Timeout': (int, False)
    }


class AccessLoggingPolicy(AWSProperty):
    props = {
        'EmitInterval': (int, False),
        'Enabled': (bool, True),
        'S3BucketName': (basestring, False),
        'S3BucketPrefix': (basestring, False),
    }


class LoadBalancer(AWSObject):
    type = "AWS::ElasticLoadBalancing::LoadBalancer"

    props = {
        'AccessLoggingPolicy': (AccessLoggingPolicy, False),
        'AppCookieStickinessPolicy': (list, False),
        'AvailabilityZones': (list, False),
        'ConnectionDrainingPolicy': (ConnectionDrainingPolicy, False),
        'CrossZone': (boolean, False),
        'HealthCheck': (HealthCheck, False),
        'Instances': (list, False),
        'LBCookieStickinessPolicy': (list, False),
        'LoadBalancerName': (basestring, False),
        'Listeners': (list, True),
        'Policies': (list, False),
        'Scheme': (basestring, False),
        'SecurityGroups': (list, False),
        'Subnets': (list, False),
    }

########NEW FILE########
__FILENAME__ = iam
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty, Ref
from .validators import integer
try:
    from awacs.aws import Policy
    policytypes = (dict, Policy)
except ImportError:
    policytypes = dict,


Active = "Active"
Inactive = "Inactive"


class AccessKey(AWSObject):
    type = "AWS::IAM::AccessKey"

    props = {
        'Serial': (integer, False),
        # XXX - Is Status required? Docs say yes, examples say no
        'Status': (basestring, False),
        'UserName': (basestring, True),
    }


class PolicyProps():
    props = {
        'Groups': ([basestring, Ref], False),
        'PolicyDocument': (policytypes, True),
        'PolicyName': (basestring, True),
        'Roles': ([basestring, Ref], False),
        'Users': ([basestring, Ref], False),
    }


class PolicyType(AWSObject, PolicyProps):
    # This is a top-level resource
    type = "AWS::IAM::Policy"


class Policy(AWSProperty, PolicyProps):
    # This is for use in a list with Group (below)
    pass


class Group(AWSObject):
    type = "AWS::IAM::Group"

    props = {
        'Path': (basestring, False),
        'Policies': ([Policy], False),
    }


class InstanceProfile(AWSObject):
    type = "AWS::IAM::InstanceProfile"

    props = {
        'Path': (basestring, True),
        'Roles': (list, True),
    }


class Role(AWSObject):
    type = "AWS::IAM::Role"

    props = {
        'AssumeRolePolicyDocument': (policytypes, True),
        'Path': (basestring, True),
        'Policies': ([Policy], False),
    }


class LoginProfile(AWSHelperFn):
    def __init__(self, data):
        self.data = {'Password': data}

    def JSONrepr(self):
        return self.data


class User(AWSObject):
    type = "AWS::IAM::User"

    props = {
        'Path': (basestring, False),
        'Groups': ([basestring, Ref], False),
        'LoginProfile': (LoginProfile, False),
        'Policies': ([Policy], False),
    }


class UserToGroupAddition(AWSObject):
    type = "AWS::IAM::UserToGroupAddition"

    props = {
        'GroupName': (basestring, True),
        'Users': (list, True),
    }

########NEW FILE########
__FILENAME__ = kinesis
# Copyright (c) 2014, Guillem Anguera <ganguera@gmail.com>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject
from .validators import integer


class Stream(AWSObject):
    type = "AWS::Kinesis::Stream"

    props = {
        'ShardCount': (integer, False),
    }

########NEW FILE########
__FILENAME__ = heat
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# Copyright (c) 2014, Andy Botting <andy.botting@theguardian.com>
# All rights reserved.
#
# See LICENSE file for full license.

from troposphere import AWSObject
from troposphere.validators import integer


# Due to the strange nature of the OpenStack compatability layer, some values
# that should be integers fail to validate and need to be represented as
# strings. For this reason, we duplicate the AWS::AutoScaling::AutoScalingGroup
# and change these types.
class AWSAutoScalingGroup(AWSObject):
    type = "AWS::AutoScaling::AutoScalingGroup"

    props = {
        'AvailabilityZones': (list, True),
        'Cooldown': (integer, False),
        'DesiredCapacity': (basestring, False),
        'HealthCheckGracePeriod': (int, False),
        'HealthCheckType': (basestring, False),
        'LaunchConfigurationName': (basestring, True),
        'LoadBalancerNames': (list, False),
        'MaxSize': (basestring, True),
        'MinSize': (basestring, True),
        'Tags': (list, False),
        'VPCZoneIdentifier': (list, False),
    }

########NEW FILE########
__FILENAME__ = neutron
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# Copyright (c) 2014, Andy Botting <andy.botting@theguardian.com>
# All rights reserved.
#
# See LICENSE file for full license.


from troposphere import AWSObject, AWSProperty
from troposphere.validators import boolean, integer, integer_range
from troposphere.validators import network_port, positive_integer


class Firewall(AWSObject):
    type = "OS::Neutron::Firewall"

    props = {
        'admin_state_up': (boolean, False),
        'description': (basestring, False),
        'firewall_policy_id': (basestring, True),
        'name': (basestring, False),
    }


class FirewallPolicy(AWSObject):
    type = "OS::Neutron::FirewallPolicy"

    props = {
        'audited': (boolean, False),
        'description': (basestring, False),
        'firewall_rules': (list, True),
        'name': (basestring, False),
        'shared': (boolean, False),
    }


class FirewallRule(AWSObject):
    type = "OS::Neutron::FirewallRule"

    props = {
        'action': (basestring, False),
        'description': (basestring, False),
        'destination_ip_address': (basestring, False),
        'destination_port': (network_port, False),
        'enabled': (boolean, False),
        'ip_version': (basestring, False),
        'name': (basestring, False),
        'protocol': (basestring, False),
        'shared': (boolean, False),
        'source_ip_address': (basestring, False),
        'source_port': (network_port, False),
    }

    def validate(self):
        if 'action' in self.resource:
            action = self.resource['action']
            if action not in ['allow', 'deny']:
                raise ValueError(
                    "The action attribute must be "
                    "either allow or deny")

        if 'ip_version' in self.resource:
            ip_version = self.resource['ip_version']
            if ip_version not in ['4', '6']:
                raise ValueError(
                    "The ip_version attribute must be "
                    "either 4 or 6")

        if 'protocol' in self.resource:
            protocol = self.resource['protocol']
            if protocol not in ['tcp', 'udp', 'icmp', None]:
                raise ValueError(
                    "The protocol attribute must be "
                    "either tcp, udp, icmp or None")

        return True


class FloatingIP(AWSObject):
    type = "OS::Neutron::FloatingIP"

    props = {
        'fixed_ip_address': (basestring, False),
        'floating_network_id': (basestring, True),
        'port_id': (basestring, False),
        'value_specs': (dict, False),
    }


class FloatingIPAssociation(AWSObject):
    type = "OS::Neutron::FloatingIPAssociation"

    props = {
        'fixed_ip_address': (basestring, False),
        'floatingip_id': (basestring, True),
        'port_id': (basestring, False),
    }


class HealthMonitor(AWSObject):
    type = "OS::Neutron::HealthMonitor"

    props = {
        'admin_state_up': (boolean, False),
        'delay': (positive_integer, True),
        'expected_codes': (basestring, False),
        'http_method': (basestring, False),
        'max_retries': (integer, True),
        'timeout': (integer, True),
        'type': (basestring, True),
        'url_path': (basestring, False),
    }

    def validate(self):

        if 'type' in self.resource:
            mon_type = self.resource['type']
            if mon_type not in ['PING', 'TCP', 'HTTP', 'HTTPS']:
                raise ValueError(
                    "The type attribute must be "
                    "either PING, TCP, HTTP or HTTPS")

        return True


class SessionPersistence(AWSProperty):
    props = {
        'cookie_name': (basestring, False),
        'type': (basestring, False),
    }

    def validate(self):
        if 'type' in self.resource:
            if 'cookie_name' not in self.resource:
                raise ValueError(
                    "The cookie_name attribute must be "
                    "given if session type is APP_COOKIE")

            session_type = self.resource['type']
            if session_type not in ['SOURCE_IP', 'HTTP_COOKIE', 'APP_COOKIE']:
                raise ValueError(
                    "The type attribute must be "
                    "either SOURCE_IP, HTTP_COOKIE or APP_COOKIE")

        return True


class VIP(AWSProperty):
    props = {
        'address': (basestring, False),
        'admin_state_up': (boolean, False),
        'connection_limit': (integer, True),
        'description': (basestring, False),
        'name': (basestring, False),
        'protocol_port': (network_port, True),
        'session_persistence': (SessionPersistence, False),
    }


class Pool(AWSObject):
    type = "OS::Neutron::Pool"

    props = {
        'admin_state_up': (boolean, False),
        'description': (basestring, False),
        'lb_method': (basestring, True),
        'monitors': (list, False),
        'name': (basestring, False),
        'protocol': (basestring, True),
        'subnet_id': (basestring, True),
        'vip': (VIP, False),
    }

    def validate(self):

        if 'lb_method' in self.resource:
            lb_method = self.resource['lb_method']
            if lb_method not in ['ROUND_ROBIN', 'LEAST_CONNECTIONS',
                                 'SOURCE_IP']:
                raise ValueError(
                    "The lb_method attribute must be "
                    "either ROUND_ROBIN, LEAST_CONNECTIONS "
                    "or SOURCE_IP")

        if 'protocol' in self.resource:
            protocol = self.resource['protocol']
            if protocol not in ['TCP', 'HTTP', 'HTTPS']:
                raise ValueError(
                    "The type attribute must be "
                    "either TCP, HTTP or HTTPS")

        return True


class LoadBalancer(AWSObject):
    type = "OS::Neutron::LoadBalancer"

    props = {
        'members': (list, False),
        'pool_id': (Pool, True),
        'protocol_port': (network_port, True),
    }


class Net(AWSObject):
    type = "OS::Neutron::Net"

    props = {
        'admin_state_up': (boolean, False),
        'name': (basestring, False),
        'shared': (boolean, False),
        'tenant_id': (basestring, False),
        'value_specs': (dict, False),
    }


class PoolMember(AWSObject):
    type = "OS::Neutron::PoolMember"

    props = {
        'address': (basestring, True),
        'admin_state_up': (boolean, False),
        'pool_id': (Pool, True),
        'protocol_port': (network_port, True),
        'weight': (integer_range(0, 256), False),
    }


class AddressPair(AWSProperty):
    props = {
        'ip_address': (basestring, True),
        'mac_address': (basestring, False),
    }


class FixedIP(AWSProperty):
    props = {
        'ip_address': (basestring, False),
        'subnet_id': (basestring, False),
    }


class Port(AWSObject):
    type = "OS::Neutron::Port"

    props = {
        'admin_state_up': (boolean, False),
        'allowed_address_pairs': (list, False),
        'security_groups': (list, True),
        'device_id': (basestring, False),
        'fixed_ips': (list, False),
        'mac_address': (basestring, False),
        'name': (basestring, False),
        'network_id': (basestring, True),
        'security_groups': (list, False),
        'value_specs': (dict, False),
    }


class SecurityGroup(AWSObject):
    type = "OS::Neutron::SecurityGroup"

    props = {
        'description': (basestring, True),
        'name': (basestring, False),
        'rules': (list, False),
    }


class SecurityGroupRule(AWSProperty):
    props = {
        'direction': (basestring, False),
        'ethertype': (basestring, False),
        'port_range_max': (network_port, False),
        'port_range_min': (network_port, False),
        'protocol': (basestring, False),
        'remote_group_id': (basestring, False),
        'remote_ip_prefix': (basestring, False),
        'remote_mode': (basestring, False),
    }

    def validate(self):
        if 'direction' in self.resource:
            direction = self.resource['direction']
            if direction not in ['ingress', 'egress']:
                raise ValueError(
                    "The direction attribute must be "
                    "either ingress or egress")

        if 'ethertype' in self.resource:
            ethertype = self.resource['ethertype']
            if ethertype not in ['IPv4', 'IPv6']:
                raise ValueError(
                    "The ethertype attribute must be "
                    "either IPv4 or IPv6")

        if 'protocol' in self.resource:
            protocol = self.resource['protocol']
            if protocol not in ['tcp', 'udp', 'icmp']:
                raise ValueError(
                    "The protocol attribute must be "
                    "either tcp, udp or icmp")

        if 'remote_mode' in self.resource:
            remote_mode = self.resource['remote_mode']
            if remote_mode not in ['remote_ip_prefix', 'remote_group_id']:
                raise ValueError(
                    "The remote_mode attribute must be "
                    "either remote_ip_prefix or remote_group_id")

        return True

########NEW FILE########
__FILENAME__ = nova
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# Copyright (c) 2014, Andy Botting <andy.botting@theguardian.com>
# All rights reserved.
#
# See LICENSE file for full license.


from troposphere import AWSObject, AWSProperty
from troposphere.validators import boolean, integer, network_port


class BlockDeviceMapping(AWSProperty):
    props = {
        'delete_on_termination': (boolean, False),
        'device_name': (basestring, True),
        'snapshot_id': (basestring, False),
        'volume_id': (basestring, False),
        'volume_size': (integer, False),
    }


class Network(AWSProperty):
    props = {
        'fixed_ip': (basestring, False),
        'network': (basestring, False),
        'port': (network_port, False),
    }


class FloatingIP(AWSObject):
    type = "OS::Nova::FloatingIP"

    props = {
        'pool': (basestring, False),
    }


class FloatingIPAssociation(AWSObject):
    type = "OS::Nova::FloatingIPAssociation"

    props = {
        'floating_ip': (basestring, True),
        'server_ip': (basestring, True),
    }


class KeyPair(AWSObject):
    type = "OS::Nova::KeyPair"

    props = {
        'name': (basestring, True),
        'public_key': (basestring, False),
        'save_private_key': (boolean, False),
    }


class Server(AWSObject):
    type = "OS::Nova::Server"

    props = {
        'admin_pass': (basestring, False),
        'admin_user': (basestring, False),
        'availability_zone': (basestring, False),
        'block_device_mapping': (list, False),
        'config_drive': (basestring, False),
        'diskConfig': (basestring, False),
        'flavor': (basestring, False),
        'flavor_update_policy': (basestring, False),
        'image': (basestring, True),
        'image_update_policy': (basestring, False),
        'key_name': (basestring, False),
        'metadata': (dict, False),
        'name': (basestring, False),
        'personality': (dict, False),
        'networks': (list, True),
        'reservation_id': (basestring, False),
        'scheduler_hints': (dict, False),
        'security_groups': (list, False),
        'software_config_transport': (basestring, False),
        'user_data': (basestring, False),
        'user_data_format': (basestring, False),
    }

    def validate(self):
        if 'diskConfig' in self.resource:
            diskConfig = self.resource['diskConfig']
            if diskConfig not in ['AUTO', 'MANUAL']:
                raise ValueError(
                    "The diskConfig attribute "
                    "must be either AUTO or MANUAL")

        if 'flavor_update_policy' in self.resource:
            flavor_update_policy = self.resource['flavor_update_policy']
            if flavor_update_policy not in ['RESIZE', 'REPLACE']:
                raise ValueError(
                    "The flavor_update_policy attribute "
                    "must be either RESIZE or REPLACE")

        if 'image_update_policy' in self.resource:
            image_update_policy = self.resource['flavor_update_policy']
            if image_update_policy not in ['REBUILD', 'REPLACE',
                                           'REBUILD_PRESERVE_EPHEMERAL']:
                raise ValueError(
                    "The image_update_policy attribute "
                    "must be either REBUILD, REPLACE or "
                    "REBUILD_PRESERVE_EPHEMERAL")

        if 'software_config_transport' in self.resource:
            sct = self.resource['software_config_transport']
            if sct not in ['POLL_SERVER_CFN', 'POLL_SERVER_HEAT']:
                raise ValueError(
                    "The software_config_transport attribute "
                    "must be either POLL_SERVER_CFN or POLL_SERVER_HEAT")

        if 'user_data_format' in self.resource:
            user_data_format = self.resource['user_data_format']
            if user_data_format not in ['HEAT_CFNTOOLS', 'RAW']:
                raise ValueError(
                    "The user_data_format attribute "
                    "must be either HEAT_CFNTOOLS or RAW")

        return True

########NEW FILE########
__FILENAME__ = opsworks
# Copyright (c) 2014, Yuta Okamoto <okapies@gmail.com>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty, Ref
from .validators import boolean, integer


class Source(AWSProperty):
    props = {
        'Password': (basestring, False),
        'Revision': (basestring, False),
        'SshKey': (basestring, False),
        'Type': (basestring, False),
        'Url': (basestring, False),
        'Username': (basestring, False),
    }


class SslConfiguration(AWSProperty):
    props = {
        'Certificate': (basestring, True),
        'Chain': (basestring, False),
        'PrivateKey': (basestring, True),
    }


class Recipes(AWSProperty):
    props = {
        'Configure': ([basestring], False),
        'Deploy': ([basestring], False),
        'Setup': ([basestring], False),
        'Shutdown': ([basestring], False),
        'Undeploy': ([basestring], False),
    }


class VolumeConfiguration(AWSProperty):
    props = {
        'MountPoint': (basestring, True),
        'NumberOfDisks': (integer, True),
        'RaidLevel': (integer, False),
        'Size': (integer, True),
    }


class StackConfigurationManager(AWSProperty):
    props = {
        'Name': (basestring, False),
        'Version': (basestring, False),
    }


class App(AWSObject):
    type = "AWS::OpsWorks::App"

    props = {
        'AppSource': (Source, False),
        'Attributes': (dict, False),
        'Description': (basestring, False),
        'Domains': ([basestring], False),
        'EnableSsl': (boolean, False),
        'Name': (basestring, True),
        'Shortname': (basestring, False),
        'SslConfiguration': (SslConfiguration, False),
        'StackId': (basestring, True),
        'Type': (basestring, True),
    }


class ElasticLoadBalancerAttachment(AWSObject):
    type = "AWS::OpsWorks::ElasticLoadBalancerAttachment"

    props = {
        'ElasticLoadBalancerName': (basestring, True),
        'LayerId': (basestring, True),
    }


class Instance(AWSObject):
    type = "AWS::OpsWorks::Instance"

    props = {
        'AmiId': (basestring, False),
        'Architecture': (basestring, False),
        'AvailabilityZone': (basestring, False),
        'InstallUpdatesOnBoot': (boolean, False),
        'InstanceType': (basestring, True),
        'LayerIds': ([basestring, Ref], True),
        'Os': (basestring, False),
        'RootDeviceType': (basestring, False),
        'SshKeyName': (basestring, False),
        'StackId': (basestring, True),
        'SubnetId': (basestring, False),
    }


class Layer(AWSObject):
    type = "AWS::OpsWorks::Layer"

    props = {
        'Attributes': (dict, False),
        'AutoAssignElasticIps': (boolean, True),
        'AutoAssignPublicIps': (boolean, True),
        'CustomInstanceProfileArn': (basestring, False),
        'CustomRecipes': (Recipes, False),
        'CustomSecurityGroupIds': ([basestring, Ref], False),
        'EnableAutoHealing': (boolean, True),
        'InstallUpdatesOnBoot': (boolean, False),
        'Name': (basestring, True),
        'Packages': ([basestring], False),
        'Shortname': (basestring, True),
        'StackId': (basestring, True),
        'Type': (basestring, True),
        'VolumeConfigurations': ([VolumeConfiguration], False),
    }


class Stack(AWSObject):
    type = "AWS::OpsWorks::Stack"

    props = {
        'Attributes': (dict, False),
        'ConfigurationManager': (StackConfigurationManager, False),
        'CustomCookbooksSource': (Source, False),
        'CustomJson': (basestring, False),  # TODO: JSON object
        'DefaultAvailabilityZone': (basestring, False),
        'DefaultInstanceProfileArn': (basestring, True),
        'DefaultOs': (basestring, False),
        'DefaultRootDeviceType': (basestring, False),
        'DefaultSshKeyName': (basestring, False),
        'DefaultSubnetId': (basestring, False),
        'HostnameTheme': (basestring, False),
        'Name': (basestring, True),
        'ServiceRoleArn': (basestring, True),
        'UseCustomCookbooks': (boolean, False),
        'VpcId': (basestring, False),
    }

########NEW FILE########
__FILENAME__ = rds
# Copyright (c) 2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty
from .validators import boolean


class DBInstance(AWSObject):
    type = "AWS::RDS::DBInstance"

    props = {
        'AllocatedStorage': (basestring, True),
        'AutoMinorVersionUpgrade': (boolean, False),
        'AvailabilityZone': (basestring, False),
        'BackupRetentionPeriod': (basestring, False),
        'DBInstanceClass': (basestring, True),
        'DBInstanceIdentifier': (basestring, False),
        'DBName': (basestring, False),
        'DBParameterGroupName': (basestring, False),
        'DBSecurityGroups': (list, False),
        'DBSnapshotIdentifier': (basestring, False),
        'DBSubnetGroupName': (basestring, False),
        'Engine': (basestring, True),
        'EngineVersion': (basestring, False),
        'Iops': (int, False),
        'LicenseModel': (basestring, False),
        'MasterUsername': (basestring, True),
        'MasterUserPassword': (basestring, True),
        'MultiAZ': (boolean, False),
        'Port': (basestring, False),
        'PreferredBackupWindow': (basestring, False),
        'PreferredMaintenanceWindow': (basestring, False),
        'SourceDBInstanceIdentifier': (basestring, False),
        'Tags': (list, False),
        'VPCSecurityGroups': ([basestring, AWSHelperFn], False),
    }


class DBParameterGroup(AWSObject):
    type = "AWS::RDS::DBParameterGroup"

    props = {
        'Description': (basestring, False),
        'Family': (basestring, False),
        'Parameters': (dict, False),
        'Tags': (list, False),
    }


class DBSubnetGroup(AWSObject):
    type = "AWS::RDS::DBSubnetGroup"

    props = {
        'DBSubnetGroupDescription': (basestring, True),
        'SubnetIds': (list, True),
        'Tags': (list, False),
    }


class RDSSecurityGroup(AWSProperty):
    props = {
        'CIDRIP': (basestring, False),
        'EC2SecurityGroupId': (basestring, False),
        'EC2SecurityGroupName': (basestring, False),
        'EC2SecurityGroupOwnerId': (basestring, False),
    }


class DBSecurityGroup(AWSObject):
    type = "AWS::RDS::DBSecurityGroup"

    props = {
        'EC2VpcId': (basestring, False),
        'DBSecurityGroupIngress': (list, True),
        'GroupDescription': (basestring, True),
        'Tags': (list, False),
    }


class DBSecurityGroupIngress(AWSObject):
    type = "AWS::RDS::DBSecurityGroupIngress"

    props = {
        'CIDRIP': (basestring, False),
        'DBSecurityGroupName': (basestring, True),
        'EC2SecurityGroupId': (basestring, True),
        'EC2SecurityGroupName': (basestring, True),
        'EC2SecurityGroupOwnerId': (basestring, True),
    }

########NEW FILE########
__FILENAME__ = route53
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSHelperFn, AWSObject, AWSProperty
from .validators import integer


class AliasTarget(AWSHelperFn):
    def __init__(self, hostedzoneid, dnsname):
        self.data = {
            'HostedZoneId': hostedzoneid,
            'DNSName': dnsname,
        }

    def JSONrepr(self):
        return self.data


class BaseRecordSet(object):
    props = {
        'AliasTarget': (AliasTarget, False),
        'Comment': (basestring, False),
        'HostedZoneId': (basestring, False),
        'HostedZoneName': (basestring, False),
        'Name': (basestring, True),
        'Region': (basestring, False),
        'ResourceRecords': (list, False),
        'SetIdentifier': (basestring, False),
        'TTL': (integer, False),
        'Type': (basestring, True),
        'Weight': (integer, False),
    }


class RecordSetType(AWSObject, BaseRecordSet):
    # This is a top-level resource
    type = "AWS::Route53::RecordSet"


class RecordSet(AWSProperty, BaseRecordSet):
    # This is for use in a list with RecordSetGroup (below)
    pass


class RecordSetGroup(AWSObject):
    type = "AWS::Route53::RecordSetGroup"

    props = {
        'HostedZoneId': (basestring, False),
        'HostedZoneName': (basestring, False),
        'RecordSets': (list, False),
        'Comment': (basestring, False),
    }

########NEW FILE########
__FILENAME__ = s3
# Copyright (c) 2013, Bob Van Zant <bob@veznat.com>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty, Tags
try:
    from awacs.aws import Policy
    policytypes = (dict, Policy)
except ImportError:
    policytypes = dict,


Private = "Private"
PublicRead = "PublicRead"
PublicReadWrite = "PublicReadWrite"
AuthenticatedRead = "AuthenticatedRead"
BucketOwnerRead = "BucketOwnerRead"
BucketOwnerFullControl = "BucketOwnerFullControl"


class WebsiteConfiguration(AWSProperty):
    props = {
        'IndexDocument': (basestring, False),
        'ErrorDocument': (basestring, False),
    }


class Bucket(AWSObject):
    type = "AWS::S3::Bucket"

    props = {
        'AccessControl': (basestring, False),
        'BucketName': (basestring, False),
        'Tags': (Tags, False),
        'WebsiteConfiguration': (WebsiteConfiguration, False)
    }

    access_control_types = [
        Private,
        PublicRead,
        PublicReadWrite,
        AuthenticatedRead,
        BucketOwnerRead,
        BucketOwnerFullControl,
    ]

    def __init__(self, name, **kwargs):
        super(Bucket, self).__init__(name, **kwargs)

        if 'AccessControl' in kwargs:
            if kwargs['AccessControl'] not in self.access_control_types:
                raise ValueError('AccessControl must be one of "%s"' % (
                    ', '.join(self.access_control_types)))


class BucketPolicy(AWSObject):
    type = "AWS::S3::BucketPolicy"

    props = {
        'Bucket': (basestring, True),
        'PolicyDocument': (policytypes, True),
    }

########NEW FILE########
__FILENAME__ = sdb
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject


class Domain(AWSObject):
    type = "AWS::SDB::Domain"

    props = {}

########NEW FILE########
__FILENAME__ = sns
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty
try:
    from awacs.aws import Policy
    policytypes = (dict, Policy)
except ImportError:
    policytypes = dict,


class Subscription(AWSProperty):
    props = {
        'Endpoint': (basestring, True),
        'Protocol': (basestring, True),
    }


class TopicPolicy(AWSObject):
    type = "AWS::SNS::TopicPolicy"

    props = {
        'PolicyDocument': (policytypes, True),
        'Topics': (list, True),
    }


class Topic(AWSObject):
    type = "AWS::SNS::Topic"

    props = {
        'DisplayName': (basestring, False),
        'Subscription': ([Subscription], True),
        'TopicName': (basestring, False),
    }

########NEW FILE########
__FILENAME__ = sqs
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.

from . import AWSObject, AWSProperty
from .validators import integer
try:
    from awacs.aws import Policy
    policytypes = (dict, Policy)
except ImportError:
    policytypes = dict,


class RedrivePolicy(AWSProperty):
    props = {
        'deadLetterTargetArn': (basestring, False),
        'maxReceiveCount': (integer, False),
    }


class Queue(AWSObject):
    type = "AWS::SQS::Queue"

    props = {
        'DelaySeconds': (integer, False),
        'MaximumMessageSize': (integer, False),
        'MessageRetentionPeriod': (integer, False),
        'QueueName': (basestring, False),
        'ReceiveMessageWaitTimeSeconds': (integer, False),
        'RedrivePolicy': (RedrivePolicy, False),
        'VisibilityTimeout': (integer, False),
    }


class QueuePolicy(AWSObject):
    type = "AWS::SQS::QueuePolicy"

    props = {
        'PolicyDocument': (policytypes, False),
        'Queues': (list, True),
    }

########NEW FILE########
__FILENAME__ = validators
# Copyright (c) 2012-2013, Mark Peek <mark@peek.org>
# All rights reserved.
#
# See LICENSE file for full license.


def boolean(x):
    if x in [True, 1, '1', 'true', 'True']:
        return "true"
    if x in [False, 0, '0', 'false', 'False']:
        return "false"
    raise ValueError


def integer(x):
    try:
        int(x)
    except (ValueError, TypeError):
        raise ValueError("%r is not a valid integer" % x)
    else:
        return x


def positive_integer(x):
    p = integer(x)
    if int(p) < 0:
        raise ValueError("%r is not a positive integer" % x)
    return x


def integer_range(minimum_val, maximum_val):
    def integer_range_checker(x):
        i = int(x)
        if i < minimum_val or i > maximum_val:
            raise ValueError('Integer must be between %d and %d' % (
                minimum_val, maximum_val))
        return x

    return integer_range_checker


def network_port(x):
    from . import AWSHelperFn

    # Network ports can be Ref items
    if isinstance(x, AWSHelperFn):
        return x

    i = integer(x)
    if int(i) < -1 or int(i) > 65535:
        raise ValueError("network port %r must been between 0 and 65535" % i)
    return x

########NEW FILE########
