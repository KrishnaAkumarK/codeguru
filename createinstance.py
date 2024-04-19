import boto3
import botocore

# Replace with your public IP address
my_ip = ' 106.51.80.59/32'

# Create an EC2 resource
ec2 = boto3.resource('ec2')

# Create an IAM resource
iam = boto3.resource('iam')

# Create an IAM role for EC2 instances with SSM permissions
role_name = 'EC2InstanceRole'
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
role = iam.create_role(
    RoleName=role_name,
    AssumeRolePolicyDocument=str(assume_role_policy_document)
)

# Attach the AmazonSSMManagedInstanceCore managed policy to the role
ssm_managed_policy_arn = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
role.attach_policy(PolicyArn=ssm_managed_policy_arn)

# Create an instance profile for the role
instance_profile = iam.create_instance_profile(
    InstanceProfileName=role_name,
    Path='/'
)
instance_profile.add_role(RoleName=role.name)

# Create a VPC
vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
vpc.create_tags(Tags=[{"Key": "Name", "Value": "MyVPC"}])
vpc.wait_until_available()
print(f"VPC created: {vpc.id}")

# Create two public subnets
public_subnet1 = vpc.create_subnet(CidrBlock='10.0.0.0/24', AvailabilityZone='us-east-1a')
public_subnet1.create_tags(Tags=[{"Key": "Name", "Value": "PublicSubnet1"}])
print(f"Public subnet 1 created: {public_subnet1.id}")

public_subnet2 = vpc.create_subnet(CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1b')
public_subnet2.create_tags(Tags=[{"Key": "Name", "Value": "PublicSubnet2"}])
print(f"Public subnet 2 created: {public_subnet2.id}")

# Create a private subnet
private_subnet = vpc.create_subnet(CidrBlock='10.0.2.0/24', AvailabilityZone='us-east-1c')
private_subnet.create_tags(Tags=[{"Key": "Name", "Value": "PrivateSubnet"}])
print(f"Private subnet created: {private_subnet.id}")

# Create an Internet Gateway
internet_gateway = ec2.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=internet_gateway.id)
print("Internet Gateway created and attached to VPC")

# Create a NAT Gateway
eip = ec2.allocate_address(Domain='vpc')
print(f"Elastic IP allocated: {eip.public_ip}")

nat_gateway = ec2.create_nat_gateway(AllocationId=eip.allocation_id, SubnetId=public_subnet1.id)
nat_gateway.wait_until_available()
print(f"NAT Gateway created: {nat_gateway.id}")

# Create route tables
public_route_table = vpc.create_route_table()
public_route_table.create_tags(Tags=[{"Key": "Name", "Value": "PublicRouteTable"}])
public_route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internet_gateway.id)

private_route_table = vpc.create_route_table()
private_route_table.create_tags(Tags=[{"Key": "Name", "Value": "PrivateRouteTable"}])
private_route_table.create_route(DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gateway.id)

# Associate route tables with subnets
public_subnet1.associate_route_table(RouteTableId=public_route_table.id)
public_subnet2.associate_route_table(RouteTableId=public_route_table.id)
private_subnet.associate_route_table(RouteTableId=private_route_table.id)

# Create Elastic Network Interfaces
public_eni = ec2.create_network_interface(SubnetId=public_subnet1.id, Groups=[])
print(f"Public ENI created: {public_eni.id}")

private_eni = ec2.create_network_interface(SubnetId=private_subnet.id, Groups=[])
print(f"Private ENI created: {private_eni.id}")

# Create security groups
public_sg = ec2.create_security_group(GroupName='PublicSG', Description='Allow HTTP and SSH', VpcId=vpc.id)
public_sg.authorize_ingress(IpPermissions=[
    {
        'FromPort': 22,
        'ToPort': 22,
        'IpProtocol': 'tcp',
        'IpRanges': [{'CidrIp': my_ip, 'Description': 'My IP'}]
    },
    {
        'FromPort': 80,
        'ToPort': 80,
        'IpProtocol': 'tcp',
        'IpRanges': [{'CidrIp': my_ip, 'Description': 'My IP'}]
    }
])
print(f"Public security group created: {public_sg.id}")

private_sg = ec2.create_security_group(GroupName='PrivateSG', Description='Allow SSH', VpcId=vpc.id)
private_sg.authorize_ingress(IpPermissions=[
    {
        'FromPort': 22,
        'ToPort': 22,
        'IpProtocol': 'tcp',
        'IpRanges': [{'CidrIp': public_eni.private_ip_address + '/32', 'Description': 'Public Instance IP'}]
    }
])
print(f"Private security group created: {private_sg.id}")

# Create EC2 instances
public_instance = ec2.create_instances(
    ImageId='ami-0aa7d40eeae50c9a9',
    InstanceType='t2.micro',
    MaxCount=1,
    MinCount=1,
    NetworkInterfaces=[{'NetworkInterfaceId': public_eni.id, 'DeviceIndex': 0}],
    KeyName='your_key_pair_name',
    IamInstanceProfile={'Name': instance_profile.name}
)[0]
print(f"Public EC2 instance created: {public_instance.id}")

private_instance = ec2.create_instances(
    ImageId='ami-0aa7d40eeae50c9a9',
    InstanceType='t2.micro',
    MaxCount=1,
    MinCount=1,
    NetworkInterfaces=[{'NetworkInterfaceId': private_eni.id, 'DeviceIndex': 0}],
    KeyName='your_key_pair_name'
)[0]
print(f"Private EC2 instance created: {private_instance.id}")
