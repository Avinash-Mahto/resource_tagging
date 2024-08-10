import boto3

# Function to fetch ARNs of resources that are missing a specific tag key
def fetch_resource_arns():
    try:
        client = boto3.client('resource-explorer-2')
        
        # Define the default view ARN for AWS Resource Explorer
        default_view_arn = "arn:aws:resource-explorer-2:us-east-1:667436281568165:view/all-resources/fc874ae2-4a53-4b7e-a53gdhsag5453hsgvas"
        
        # Query to identify resources missing a specific tag key
        query_filter = '-tag.key:Lab'
        
        # List to collect resource ARNs
        resource_arns = []
        
        # Utilize paginator to manage multiple pages of search results
        paginator = client.get_paginator('search')
        response_pages = paginator.paginate(
            QueryString=query_filter,
            ViewArn=default_view_arn
        )
        
        for response in response_pages:
            resource_items = response['Resources']
            for resource in resource_items:
                resource_arns.append(resource['Arn'])
        
        # Ensure uniqueness by converting to a set and back to a list
        return list(set(resource_arns))
    except Exception as error:
        print(f"Failed to retrieve resource ARNs: {error}")

# Function to categorize resources by their region
def categorize_resources_by_region(resource_arns):
    try:
        # Dictionary to hold resources grouped by region
        regional_resources = {}
        
        for arn in resource_arns:
            if ':' in arn:
                # Extract the region from the ARN (3rd part in ARN)
                region = arn.split(':')[3]
                if region not in regional_resources:
                    regional_resources[region] = []
                regional_resources[region].append(arn)
        
        return regional_resources
    except Exception as error:
        print(f"Error while grouping resources by region: {error}")

# Function to apply the 'ENV: Prod' tag to resources grouped by region
def apply_tags_to_resources_by_region(resource_groups):
    try:
        untagged_resources = []
        for region, resources in resource_groups.items():
            # Create a tagging client for the specified region
            if region:
                tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region)
            else:
                tagging_client = boto3.client('resourcegroupstaggingapi', region_name="us-east-1")
            
            # Split resources into batches of 20 (API limit)
            resource_batches = [resources[i:i + 20] for i in range(0, len(resources), 20)]
            
            for batch in resource_batches:
                # Apply the 'ENV: Prod' tag to the batch of resources
                tag_result = tagging_client.tag_resources(
                    ResourceARNList=batch,
                    Tags={'ENV': 'Prod'}
                )
                # Collect ARNs of resources that failed to be tagged
                if tag_result.get('FailedResourcesMap'):
                    untagged_resources.extend(tag_result['FailedResourcesMap'].keys())
        
        return untagged_resources
    except Exception as error:
        print(f"Tagging failed for some resources: {error}")

# Main function for the AWS Lambda handler
def lambda_handler(event, context):
    try:
        print("Execution started...")
        # Fetch the list of resources missing the specific tag
        resources = fetch_resource_arns()
        if resources:
            print("Grouping resources by region...")
            # Group the resources by their region
            grouped_resources = categorize_resources_by_region(resources)
            if grouped_resources:
                print("Applying tags to grouped resources...")
                # Apply the 'ENV: Prod' tag to the resources
                tagging_errors = apply_tags_to_resources_by_region(grouped_resources)
                print(tagging_errors)
                # Log the number of resources that failed to be tagged
                print(f"Number of untagged resources: {len(tagging_errors)}")
    except Exception as error:
        print(f"Error during lambda execution: {error}")
