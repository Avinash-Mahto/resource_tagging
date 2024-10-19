import boto3
import requests
from datetime import datetime, timezone, timedelta

iam_client = boto3.client('iam')
sts_client = boto3.client('sts')  # To get the AWS account ID

# Fetch the account ID dynamically
account_id = sts_client.get_caller_identity()['Account']

def check_least_privilege(role):
    # Implement least privilege check logic here
    pass

def check_trusted_entities(role):
    # Implement trusted entities check logic here
    pass

def custom_script_placeholder(role):
    # Placeholder for future custom scripts
    pass

def detect_unused_role(role):
    # Check if the role has not been used for 90 days or more
    role_name = role['RoleName']
    last_used = role.get('RoleLastUsed', {}).get('LastUsedDate')

    if last_used:
        days_unused = (datetime.now(timezone.utc) - last_used).days
        if days_unused >= 90:
            return "Unused Role (>90 days)"
    else:
        return "Unused Role (Never Used)"
    
    return None  # Role is actively used

def detect_unused_permissions(role_name):
    # Construct the ARN correctly for the role
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    # Generate service last accessed details
    try:
        job = iam_client.generate_service_last_accessed_details(Arn=role_arn)
        job_id = job['JobId']

        # Poll the job status until it's complete
        while True:
            status = iam_client.get_service_last_accessed_details(JobId=job_id)
            if status['JobStatus'] == 'COMPLETED':
                break

        # Check for services with no recent access
        unused_permissions = [
            detail['ServiceNamespace'] for detail in status['ServicesLastAccessed']
            if not detail.get('LastAuthenticated')
        ]

        if unused_permissions:
            return f"Unused Permissions: {', '.join(unused_permissions)}"
        return None

    except iam_client.exceptions.NoSuchEntityException:
        return f"Role {role_name} does not exist."

    except Exception as e:
        print(f"Error retrieving access details for {role_name}: {str(e)}")
        return f"Error: {str(e)}"

def evaluate_role_compliance(role):
    # Perform all compliance checks for the role
    compliance_issues = []

    # Add custom compliance checks
    compliance_issues.append(detect_unused_role(role))
    compliance_issues.append(detect_unused_permissions(role['RoleName']))
    check_least_privilege(role)
    check_trusted_entities(role)
    custom_script_placeholder(role)

    # Filter out None values
    compliance_issues = [issue for issue in compliance_issues if issue]
    
    if compliance_issues:
        return f"NON_COMPLIANT: {', '.join(compliance_issues)}"
    return "COMPLIANT"

def generate_report(compliance_results):
    # Generate a formatted report of IAM role compliance status
    report = "IAM Role Compliance Report:\n\n"
    for role, status in compliance_results.items():
        report += f"Role: {role}, Status: {status}\n"
    return report

def send_report_to_slack(report):
    # Function to send the report to a Slack channel using a webhook URL
    slack_webhook_url = "https://hooks.slack.com/services/xxxxxxxxx/xxxxxxxx/xxxxxxxxxxxxx"  # Replace with your actual webhook URL
    payload = {"text": report}
    
    response = requests.post(slack_webhook_url, json=payload)
    if response.status_code == 200:
        print("Report successfully sent to Slack.")
    else:
        print(f"Failed to send report to Slack. Response: {response.text}")

def lambda_handler(event, context):
    # Main Lambda function handler
    roles = iam_client.list_roles()['Roles']
    compliance_results = {}

    for role in roles:
        compliance_status = evaluate_role_compliance(role)
        compliance_results[role['RoleName']] = compliance_status

    report = generate_report(compliance_results)
    send_report_to_slack(report)  # Send the generated report to Slack
