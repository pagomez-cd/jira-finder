# Jira Bug Fetcher - Usage Guide

## Overview

The `fetcher.py` script is a Python tool designed to fetch Jira issues from the Red Hat Jira instance (issues.redhat.com) and generate organized Markdown reports grouped by component.

## Features

- Fetches bugs from the PTL (Product Training and Learning) project
- Filters by component and priority level
- Supports pagination for large result sets
- Generates individual Markdown files per component
- Organizes outputs in timestamped directories
- Interactive prompts for authentication, components, and priorities

## Prerequisites

- Python 3.x
- `requests` library (`pip install requests`)
- Valid Jira Personal Access Token (PAT)

## Usage

### Running the Script

```bash
python fetcher.py
```

### Interactive Prompts

The script will guide you through three prompts:

#### 1. Authentication
```
=== Jira Bug Fetcher ===
Enter your Jira Personal Access Token (Bearer): [your-token-here]
```

#### 2. Component Selection
```
Default components: CEPH125, CEPH130, CL110, CL210, CL260, CL310, RH066X, RH104, RH124, RH134, RH199, RH174, RH236, RH254, RH318, RH342, RH354, RH362, RH403, RH415, RH436, RH442, RHS429, CL170, CL270
Enter a comma-separated list of components (or press Enter to use default):
```

**Options:**
- Press **Enter** to use all default components
- Enter specific components: `RH124, RH134, RH199`
- Enter any custom component list

#### 3. Priority Level Selection
```
Available priorities: Blocker, Critical, Major, Normal, Minor, Undefined
Default priorities: Blocker, Critical
(Type 'all' to select all priorities)
Enter a comma-separated list of priorities (or press Enter to use default):
```

**Options:**
- Press **Enter** to use default (Blocker, Critical)
- Type **all** to select all priority levels
- Enter specific priorities: `Blocker, Critical, Major`

## Output Structure

The script creates a directory structure:

```
JIRA_QUERIES/
└── YYMMDD-HHMMSS/
    ├── RH124.md
    ├── RH134.md
    └── RH199.md
```

Where:
- `YYMMDD` = Year, Month, Day (e.g., 260306 for March 6, 2026)
- `HHMMSS` = Hour, Minute, Second (e.g., 131454 for 1:14:54 PM)

Each Markdown file contains all issues for that specific component.

## Example Query

### Query Parameters
- **Components**: RH124, RH134, RH199
- **Priorities**: Blocker, Critical (default)
- **Date**: March 6, 2026 at 13:14:54

### Input Example
```
=== Jira Bug Fetcher ===
Enter your Jira Personal Access Token (Bearer): [token]

Default components: CEPH125, CEPH130, CL110, CL210, CL260, CL310, RH066X, RH104, RH124, RH134, RH199, ...
Enter a comma-separated list of components (or press Enter to use default): RH124, RH134, RH199

Available priorities: Blocker, Critical, Major, Normal, Minor, Undefined
Default priorities: Blocker, Critical
(Type 'all' to select all priorities)
Enter a comma-separated list of priorities (or press Enter to use default): [Enter]

Executing JQL query...

Successfully fetched 127 total issues.

Generating Markdown files...
  -> Created JIRA_QUERIES/260306-131454/RH124.md (45 issues)
  -> Created JIRA_QUERIES/260306-131454/RH134.md (62 issues)
  -> Created JIRA_QUERIES/260306-131454/RH199.md (20 issues)

Done! Reports are saved in the 'JIRA_QUERIES/260306-131454' directory.
```

## Analyzing Query Results

Once the Markdown files are generated, you can analyze them manually or use AI assistance.

### Example Analysis Prompt

Use this prompt with Claude or other AI tools to analyze the generated reports:

```
Analyze the Jira issues in the JIRA_QUERIES/260306-131454 directory.
Give me a summary of issues with obvious solutions.
```

### Expected Analysis Output

The AI will review all Markdown files and provide:

1. **Documentation/Content Errors**
   - Typos in commands or file paths
   - Incorrect hostnames or URLs
   - Date/version mismatches
   - Missing or incorrect syntax

2. **Lab Environment Issues**
   - Missing users or services
   - Setup script problems
   - Missing configuration commands

3. **Instructional Issues**
   - Step numbering errors
   - Solution misplacements
   - Unclear instructions

Each identified issue includes:
- Jira ticket number and link
- Brief description of the problem
- Location (course, chapter, section)
- Recommended solution

## Advanced Usage

### Filtering by Specific Priority

To fetch only high-severity issues:
```
Enter priorities: Blocker
```

To fetch medium-to-high severity:
```
Enter priorities: Blocker, Critical, Major
```

### Fetching All Priorities

To get a comprehensive view of all issues regardless of priority:
```
Enter priorities: all
```

### Custom Component Lists

To fetch issues for specific courses only:
```
Enter components: RH124, RH134
```

For Ceph-related components:
```
Enter components: CEPH125, CEPH130
```

## JQL Query Structure

The script constructs the following JQL query:

```jql
project = PTL
AND issuetype = Bug
AND component not in componentMatch(BFX0)
AND statusCategory != Done
AND component not in ("Video Content", Translations, "Learning Platform")
AND component in (RH124, RH134, RH199)
AND priority in (Blocker, Critical)
ORDER BY component desc
```

## Troubleshooting

### Authentication Errors
- Verify your Personal Access Token is valid
- Check token hasn't expired
- Ensure proper Bearer token format

### No Issues Found
- Verify components exist in the PTL project
- Check if there are open bugs for selected priorities
- Confirm network connectivity to issues.redhat.com

### Empty Markdown Files
- Some components may have no issues matching the criteria
- Try expanding priority range (use 'all')
- Check component names are spelled correctly

## Tips

1. **Start Broad**: Use default settings first to see all available issues
2. **Refine Gradually**: Use specific components and priorities for focused analysis
3. **Regular Updates**: Run queries periodically to track new issues
4. **Archive Results**: Keep timestamped directories for historical tracking
5. **Analyze Patterns**: Use AI tools to identify common issue types across components

## Support

For issues with the script or suggestions for improvements:
- Check the script's error messages
- Verify Jira API connectivity
- Review the generated JQL query in the console output
