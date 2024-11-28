import boto3
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the tagging client
tagging_client = boto3.client('resourcegroupstaggingapi')

def chunk_list(data, chunk_size):
    """Helper function to split a list into smaller chunks."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def lambda_handler(event, context):
    tag_key = "Backup"
    tag_value = "True"
    
    # Extract rollback value from the event
    rollback_value = event.get('Rollback', 'False')  # Default to 'False'
    rollback_value = rollback_value.lower() == 'true'  # Convert to boolean
    logger.info(f"Received Rollback value: {rollback_value}")

    resources_processed = 0
    total_tagged = 0
    total_untagged = 0

    try:
        # Use paginator to fetch all tagged resources
        paginator = tagging_client.get_paginator('get_resources')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            # Extract resource ARNs
            resource_list = [resource['ResourceARN'] for resource in page['ResourceTagMappingList']]
            logger.info(f"Discovered resources: {resource_list}")
            
            # Process resources in chunks of 20
            for chunk in chunk_list(resource_list, 20):
                try:
                    if rollback_value:
                        # Rollback = True: Delete Backup: True tag
                        tagging_client.untag_resources(ResourceARNList=chunk, TagKeys=[tag_key])
                        total_untagged += len(chunk)
                        logger.info(f"Deleted tag '{tag_key}' from resources: {chunk}")
                    else:
                        # Rollback = False: Add Backup: True tag
                        tagging_client.tag_resources(ResourceARNList=chunk, Tags={tag_key: tag_value})
                        total_tagged += len(chunk)
                        logger.info(f"Added tag '{tag_key}' with value '{tag_value}' to resources: {chunk}")

                    resources_processed += len(chunk)
                except Exception as e:
                    logger.error(f"Failed to process resources {chunk}: {str(e)}")

    except Exception as e:
        logger.error(f"An error occurred while retrieving or processing resources: {str(e)}")

    # Summary of the operation
    logger.info("Summary of Operation:")
    logger.info(f"Total Resources Processed: {resources_processed}")
    logger.info(f"Total Tagged: {total_tagged}")
    logger.info(f"Total Untagged: {total_untagged}")
