import boto3

def lambda_handler(event, context):
    try:
        # Extract the account ID from the event
        if 'serviceEventDetails' in event['detail']:
            account_id = event['detail']['serviceEventDetails']['createAccountStatus']['accountId']
        else:
            account_id = event['detail']['responseElements']['accountId']

        print(f"Account ID: {account_id}")
        
        # Set up the EC2 client
        ec2 = boto3.client('ec2')

        # Describe all VPCs
        vpcs = ec2.describe_vpcs()

        # Iterate through all VPCs
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            print(f"Processing VPC: {vpc_id}")

            # Describe the default security group for each VPC
            response = ec2.describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'group-name', 'Values': ['default']}
                ]
            )
            
            # Check if any security groups were returned
            if not response['SecurityGroups']:
                print(f"No default security group found in VPC {vpc_id}.")
                continue

            security_group_id = response['SecurityGroups'][0]['GroupId']
            
            # Revoke all inbound rules
            ec2.revoke_security_group_ingress(GroupId=security_group_id, IpPermissions=response['SecurityGroups'][0]['IpPermissions'])
            
            # Revoke all outbound rules
            ec2.revoke_security_group_egress(GroupId=security_group_id, IpPermissions=response['SecurityGroups'][0]['IpPermissionsEgress'])

            print(f"Removed rules from default security group {security_group_id} in VPC {vpc_id}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise
