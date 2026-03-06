import requests
import getpass
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fetcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
JIRA_BASE_URL = "https://issues.redhat.com"
SEARCH_ENDPOINT = f"{JIRA_BASE_URL}/rest/api/2/search"
DEFAULT_COMPONENTS = "CEPH125, CEPH130, CL110, CL210, CL260, CL310, RH066X, RH104, RH124, RH134, RH199, RH174, RH236, RH254, RH318, RH342, RH354, RH362, RH403, RH415, RH436, RH442, RHS429, CL170, CL270"
DEFAULT_PRIORITIES = "Blocker, Critical"
AVAILABLE_PRIORITIES = "Blocker, Critical, Major, Normal, Minor, Undefined"

# Security: Define valid components and priorities to prevent JQL injection
VALID_COMPONENTS = {
    'CEPH125', 'CEPH130', 'CL110', 'CL210', 'CL260', 'CL310',
    'RH066X', 'RH104', 'RH124', 'RH134', 'RH199', 'RH174',
    'RH236', 'RH254', 'RH318', 'RH342', 'RH354', 'RH362',
    'RH403', 'RH415', 'RH436', 'RH442', 'RHS429', 'CL170', 'CL270'
}

VALID_PRIORITIES = {'Blocker', 'Critical', 'Major', 'Normal', 'Minor', 'Undefined'}

# Configuration constants
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 0.5  # seconds between requests

# Message constants
NO_SUMMARY = "No summary provided."
NO_DESCRIPTION = "No description provided."

def parse_comma_separated(input_str: str) -> List[str]:
    """Parse and clean comma-separated input string.

    Args:
        input_str: Comma-separated string to parse

    Returns:
        List of cleaned, non-empty strings
    """
    return [item.strip() for item in input_str.split(',') if item.strip()]

def build_jql(components_str: str, priorities_str: str) -> Tuple[str, List[str]]:
    """Constructs the JQL string based on the provided components and priorities.

    Security: Validates all inputs against whitelists to prevent JQL injection.
    """
    # Clean and parse components using helper function
    comps_list = parse_comma_separated(components_str)

    # Security: Validate components against whitelist
    invalid_comps = set(comps_list) - VALID_COMPONENTS
    if invalid_comps:
        logger.error(f"Invalid components detected: {invalid_comps}")
        raise ValueError(f"Invalid components: {', '.join(invalid_comps)}. "
                        f"Valid components are: {', '.join(sorted(VALID_COMPONENTS))}")

    formatted_comps = ", ".join(comps_list)

    # Clean and parse priorities using helper function
    priorities_list = parse_comma_separated(priorities_str)

    # Security: Validate priorities against whitelist
    invalid_priorities = set(priorities_list) - VALID_PRIORITIES
    if invalid_priorities:
        logger.error(f"Invalid priorities detected: {invalid_priorities}")
        raise ValueError(f"Invalid priorities: {', '.join(invalid_priorities)}. "
                        f"Valid priorities are: {', '.join(sorted(VALID_PRIORITIES))}")

    formatted_priorities = ", ".join(priorities_list)

    jql = (
        f'project = PTL and issuetype = Bug and '
        f'component not in componentMatch(BFX0) and statusCategory != Done and '
        f'component not in ("Video Content", Translations, "Learning Platform") and '
        f'component in ({formatted_comps}) and priority in ({formatted_priorities}) '
        f'order by component desc'
    )

    logger.info(f"Generated JQL query for {len(comps_list)} components and {len(priorities_list)} priorities")
    return jql, comps_list

def get_output_directory():
    """Generates a unique directory path with format JIRA_QUERIES/YYMMDD-HHMMSS."""
    now = datetime.now()
    timestamp = now.strftime("%y%m%d-%H%M%S")
    return os.path.join("JIRA_QUERIES", timestamp)

def fetch_issues(jql: str, token: str) -> List[Dict]:
    """Fetches issues from Jira using pagination with retry logic and security improvements.

    Security improvements:
    - Request timeout to prevent hanging
    - SSL verification enforced
    - Retry logic for transient failures
    - Rate limiting to avoid overwhelming server
    - Sanitized error messages to prevent information leakage
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    issues = []
    start_at = 0
    max_results = 100  # Performance: Increased from 50 to reduce API calls
    total_issues = None

    logger.info("Executing JQL query...")
    print(f"\nExecuting JQL query...")

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "components,summary,description"
        }

        # Retry logic for resilience
        for attempt in range(MAX_RETRIES):
            try:
                # Security: Add timeout and enforce SSL verification
                response = requests.get(
                    SEARCH_ENDPOINT,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                    verify=True
                )

                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    # Security: Don't expose full response, only status code
                    logger.error(f"API request failed with status code: {response.status_code}")
                    print(f"Error fetching issues. Status Code: {response.status_code}")

                    if attempt < MAX_RETRIES - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print("Maximum retries reached. Returning partial results.")
                        return issues

                # Parse JSON response with error handling
                try:
                    data = response.json()
                except requests.exceptions.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response: {e}")
                    print("Error: Received invalid response from server")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return issues

                # Success - break retry loop
                break

            except requests.exceptions.Timeout:
                logger.error(f"Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
                print(f"Request timeout. Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    print("Maximum retries reached. Returning partial results.")
                    return issues

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {e}")
                print(f"Connection error. Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    print("Maximum retries reached. Returning partial results.")
                    return issues

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                print(f"Request failed. Retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    print("Maximum retries reached. Returning partial results.")
                    return issues

        fetched_issues = data.get("issues", [])
        issues.extend(fetched_issues)

        if total_issues is None:
            total_issues = data.get("total", 0)
            logger.info(f"Total issues to fetch: {total_issues}")

        # Progress indication
        print(f"Progress: {len(issues)}/{total_issues} issues fetched", end='\r')

        if start_at + max_results >= total_issues:
            print()  # New line after progress
            break

        start_at += max_results

        # Rate limiting: Be courteous to the API
        time.sleep(RATE_LIMIT_DELAY)

    logger.info(f"Successfully fetched {len(issues)} issues")
    return issues

def generate_markdown_files(issues: List[Dict], target_components: List[str], output_dir: str) -> None:
    """Groups issues by component and writes them to individual Markdown files.

    Args:
        issues: List of issue dictionaries from Jira API
        target_components: List of component names to filter by
        output_dir: Directory path where markdown files will be created
    """
    # Initialize dictionary to group issues by component
    issues_by_component = {comp: [] for comp in target_components}

    # Sort issues into their respective component buckets
    for issue in issues:
        key = issue.get("key")
        fields = issue.get("fields", {})
        summary = fields.get("summary", NO_SUMMARY)
        description = fields.get("description") or NO_DESCRIPTION
        components = fields.get("components", [])

        for comp in components:
            comp_name = comp.get("name")
            if comp_name in issues_by_component:
                issues_by_component[comp_name].append({
                    "key": key,
                    "summary": summary,
                    "description": description
                })

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Write to Markdown files
    print("\nGenerating Markdown files...")
    for comp_name, comp_issues in issues_by_component.items():
        if not comp_issues:
            continue  # Skip components that have no issues

        filename = os.path.join(output_dir, f"{comp_name}.md")

        # Performance: Build content in memory first, then write once
        content = [f"# Jira Issues for Component: {comp_name}\n\n"]

        for item in comp_issues:
            issue_url = f"{JIRA_BASE_URL}/browse/{item['key']}"
            content.append(f"## [{item['key']}]({issue_url}): {item['summary']}\n\n")
            content.append(f"**Description:**\n\n{item['description']}\n\n")
            content.append("---\n\n")

        # Write all content at once for better performance
        with open(filename, "w", encoding="utf-8") as f:
            f.write(''.join(content))

        print(f"  -> Created {filename} ({len(comp_issues)} issues)")

def main():
    """Main function with improved error handling and security."""
    try:
        # 1. Prompt for Authentication
        print("=== Jira Bug Fetcher ===")
        logger.info("Starting Jira Bug Fetcher")

        token = getpass.getpass("Enter your Jira Personal Access Token (Bearer): ")
        if not token:
            print("A token is required to authenticate. Exiting.")
            logger.warning("No token provided. Exiting.")
            return

        # 2. Prompt for Components
        print(f"\nDefault components: {DEFAULT_COMPONENTS}")
        custom_comps = input("Enter a comma-separated list of components (or press Enter to use default): ")

        components_to_use = custom_comps if custom_comps.strip() else DEFAULT_COMPONENTS

        # 3. Prompt for Priority Levels
        print(f"\nAvailable priorities: {AVAILABLE_PRIORITIES}")
        print(f"Default priorities: {DEFAULT_PRIORITIES}")
        print(f"(Type 'all' to select all priorities)")
        custom_priorities = input("Enter a comma-separated list of priorities (or press Enter to use default): ")

        # Handle 'all' option for priorities
        if custom_priorities.strip().lower() == 'all':
            priorities_to_use = AVAILABLE_PRIORITIES
        else:
            priorities_to_use = custom_priorities if custom_priorities.strip() else DEFAULT_PRIORITIES

        # Build JQL with validation (security: prevents injection)
        try:
            jql, target_components_list = build_jql(components_to_use, priorities_to_use)
        except ValueError as e:
            print(f"\nError: {e}")
            logger.error(f"Input validation failed: {e}")
            return

        # 4. Fetch Data
        issues = fetch_issues(jql, token)

        # 5. Generate Output
        if issues:
            print(f"\nSuccessfully fetched {len(issues)} total issues.")
            output_dir = get_output_directory()
            generate_markdown_files(issues, target_components_list, output_dir)
            print(f"\nDone! Reports are saved in the '{output_dir}' directory.")
            logger.info(f"Reports successfully saved to {output_dir}")
        else:
            print("\nNo issues found matching the criteria.")
            logger.info("No issues found")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        logger.info("Operation cancelled by user")
    except Exception as e:
        print(f"\nAn unexpected error occurred. Check fetcher.log for details.")
        logger.exception(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()