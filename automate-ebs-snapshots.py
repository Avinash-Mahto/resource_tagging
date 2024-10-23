import boto3
import datetime

ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    # Fetch all volumes in the region
    all_volumes = ec2.describe_volumes()['Volumes']
    
    # Fetch only volumes with the 'ENV=Prod' tag
    tagged_volumes = ec2.describe_volumes(
        Filters=[{'Name': 'tag:Backup', 'Values': ['True']}]
    )['Volumes']

    # Use a set to avoid duplicate entries
    unique_volumes = {v['VolumeId'] for v in all_volumes} | {v['VolumeId'] for v in tagged_volumes}

    for volume_id in unique_volumes:
        # Create a snapshot with a timestamp
        snapshot = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=f'Snapshot of {volume_id} on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )
        print(f'Snapshot created: {snapshot["SnapshotId"]}')

    return {'status': 'Snapshots created successfully'}
