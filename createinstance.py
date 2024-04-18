import boto3

def lambda_handler(event, context):
    ec2_client = boto3.client('ec2')

    response = ec2_client.run_instances(
        ImageId='ami-051f8a213df8bc089',
        InstanceType='t2.micro',
        KeyName='create_ami_instance',
        SecurityGroupIds=['sg-0acbdef2fa568e3bf'],
        SubnetId='subnet-09396588b2345a940',
        MinCount=1,
        MaxCount=1
    )

    instance_id = response['Instances'][0]['InstanceId']
    print("Instance ID:", instance_id)

    return {
        'statusCode': 200,
        'body': 'Instance launched successfully!'
    }
