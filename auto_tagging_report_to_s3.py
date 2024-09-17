import boto3
import csv
import io
import datetime

# Function to fetch ARNs of resources that are missing a specific tag key
def fetch_resource_arns():
    try:
        client = boto3.client('resource-explorer-2')
        
        default_view_arn = "arn:aws:resource-explorer-2"
        query_filter = '-tag.key:ENV'
        
        resource_arns = []
        paginator = client.get_paginator('search')
        response_pages = paginator.paginate(
            QueryString=query_filter,
            ViewArn=default_view_arn
        )
        
        for response in response_pages:
            resource_items = response['Resources']
            for resource in resource_items:
                resource_arns.append(resource['Arn'])
        
        return list(set(resource_arns))
    except Exception as error:
        print(f"Failed to retrieve resource ARNs: {error}")

# Function to categorize resources by their region
def categorize_resources_by_region(resource_arns):
    try:
        regional_resources = {}
        for arn in resource_arns:
            if ':' in arn:
                region = arn.split(':')[3]
                if region not in regional_resources:
                    regional_resources[region] = []
                regional_resources[region].append(arn)
        return regional_resources
    except Exception as error:
        print(f"Error while grouping resources by region: {error}")

# Function to apply the 'ENV: Prod' tag to resources grouped by region and track tagged/untagged
def apply_tags_to_resources_by_region(resource_groups):
    tagged_resources = []
    untagged_resources = []
    
    for region, resources in resource_groups.items():
        if region:
            tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region)
        else:
            tagging_client = boto3.client('resourcegroupstaggingapi', region_name="us-east-1")
        
        resource_batches = [resources[i:i + 20] for i in range(0, len(resources), 20)]
        
        for batch in resource_batches:
            tag_result = tagging_client.tag_resources(
                ResourceARNList=batch,
                Tags={'ENV': 'Prod'}
            )
            failed_resources = tag_result.get('FailedResourcesMap', {})
            untagged_resources.extend(failed_resources.keys())
            
            # Mark successfully tagged resources
            tagged_resources.extend([arn for arn in batch if arn not in failed_resources])
    
    return tagged_resources, untagged_resources

# Function to generate CSV report
def generate_csv_report(tagged, untagged):
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Write header
    csv_writer.writerow(["Resource ARN", "Status"])
    
    # Write tagged resources
    for arn in tagged:
        csv_writer.writerow([arn, "Tagged"])
    
    # Write untagged resources
    for arn in untagged:
        csv_writer.writerow([arn, "Untagged"])
    
    return csv_buffer.getvalue()

# Function to upload CSV report to S3
def upload_csv_to_s3(csv_data, bucket_name, file_name):
    s3_client = boto3.client('s3')
    try:
        # Upload CSV file to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=csv_data,
            ContentType='text/csv'
        )
        print(f"Report uploaded to S3: {file_name}")
    except Exception as error:
        print(f"Failed to upload report to S3: {error}")

# Main function for the AWS Lambda handler
def lambda_handler(event, context):
    try:
        print("Execution started...")
        
        # Fetch the list of resources missing the specific tag
        resources = fetch_resource_arns()
        if resources:
            print("Grouping resources by region...")
            
            # Group resources by region
            grouped_resources = categorize_resources_by_region(resources)
            
            if grouped_resources:
                print("Applying tags to grouped resources...")
                
                # Apply tags and track tagged/untagged resources
                tagged_resources, untagged_resources = apply_tags_to_resources_by_region(grouped_resources)
                
                # Generate the CSV report
                csv_report = generate_csv_report(tagged_resources, untagged_resources)
                
                # Define the S3 bucket and file name
                bucket_name = "S3-BUCKET-NAME"
                current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                file_name = f"tagging-report-{current_time}.csv"
                
                # Upload the report to S3
                upload_csv_to_s3(csv_report, bucket_name, file_name)
                
                print(f"Number of tagged resources: {len(tagged_resources)}")
                print(f"Number of untagged resources: {len(untagged_resources)}")
    except Exception as error:
        print(f"Error during lambda execution: {error}")
