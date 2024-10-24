import boto3

# Function to fetch ARNs of resources that are missing a specific tag key
def fetch_resource_arns():
    try:
        client = boto3.client('resource-explorer-2')

        default_view_arn = "arn:aws:resource-explorer-2:ap-southeast-1:XXXXXXXXXXXX:view/all-resources/6e9970cf-eb57-557dhsagdewur9u8"
        query_filter = '-tag.key:Backup'
        resource_arns = []

        paginator = client.get_paginator('search')
        response_pages = paginator.paginate(QueryString=query_filter, ViewArn=default_view_arn)

        for response in response_pages:
            for resource in response['Resources']:
                arn = resource['Arn']
                if not is_aws_managed_resource(arn):
                    resource_arns.append(arn)

        return list(set(resource_arns))
    except Exception as error:
        print(f"Failed to retrieve resource ARNs: {error}")
        return []

# Helper function to exclude AWS-managed resources
def is_aws_managed_resource(arn):
    aws_managed_keywords = ["aws:elasticloadbalancing", "aws:autoscaling", "aws:iam::aws", "aws:rds:cluster"]
    return any(keyword in arn for keyword in aws_managed_keywords)

# Group resources by their region
def categorize_resources_by_region(resource_arns):
    try:
        regional_resources = {}
        for arn in resource_arns:
            region = extract_region_from_arn(arn)
            regional_resources.setdefault(region, []).append(arn)
        return regional_resources
    except Exception as error:
        print(f"Error while grouping resources by region: {error}")
        return {}

# Extract region from ARN or use Singapore as the default
def extract_region_from_arn(arn):
    parts = arn.split(':')
    if len(parts) > 3 and parts[3]:
        return parts[3]
    else:
        print(f"Invalid or missing region in ARN: {arn}. Defaulting to 'ap-southeast-1'.")
        return "ap-southeast-1"

# Apply tags to resources by region
def apply_tags_to_resources_by_region(resource_groups):
    tagged_count = 0
    failed_count = 0
    untagged_resources = []

    for region, resources in resource_groups.items():
        try:
            tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region)

            resource_batches = [resources[i:i + 20] for i in range(0, len(resources), 20)]

            for batch in resource_batches:
                tag_result = tagging_client.tag_resources(ResourceARNList=batch, Tags={'Backup': 'True'})

                if tag_result.get('FailedResourcesMap'):
                    failed_resources = tag_result['FailedResourcesMap'].keys()
                    print(f"Failed to tag resources in region {region}: {failed_resources}")
                    untagged_resources.extend(failed_resources)
                    failed_count += len(failed_resources)

                tagged_count += len(batch) - len(tag_result.get('FailedResourcesMap', {}))
        except Exception as error:
            print(f"Error tagging resources in region {region}: {error}")
            failed_count += len(resources)

    return tagged_count, failed_count, untagged_resources

# Retry tagging for failed resources
def retry_failed_tags(untagged_resources):
    if not untagged_resources:
        return 0, 0

    print("Retrying failed resources...")
    grouped_failed_resources = categorize_resources_by_region(untagged_resources)
    retry_tagged_count, retry_failed_count, _ = apply_tags_to_resources_by_region(grouped_failed_resources)

    return retry_tagged_count, retry_failed_count

# Lambda handler function
def lambda_handler(event, context):
    print("Execution started...")

    resources = fetch_resource_arns()
    total_resources = len(resources)
    print(f"Total resources to be tagged: {total_resources}")

    if resources:
        grouped_resources = categorize_resources_by_region(resources)

        initial_tagged_count, initial_failed_count, untagged_resources = apply_tags_to_resources_by_region(grouped_resources)

        retry_tagged_count, retry_failed_count = retry_failed_tags(untagged_resources)

        total_tagged = initial_tagged_count + retry_tagged_count
        total_failed = initial_failed_count + retry_failed_count

        print("\n=== Tagging Summary ===")
        print(f"Total Resources Attempted: {total_resources}")
        print(f"Total Resources Successfully Tagged: {total_tagged}")
        print(f"Total Resources Failed to Tag: {total_failed}")
    else:
        print("No resources found that require tagging.")
