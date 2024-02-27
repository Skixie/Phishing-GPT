# SPO Automation

This package contains a script to automate parts of workflows for SPO.

## Requirements

 - Python 3.10 or newer

## Setup

Install the package using pip:

 1. `pip3 install git+ssh://git@gitlab.local.northwave.nl/mneikes/spo-automation.git`

Alternatively, for local development, clone the repo and install it as editable package:

 1. `git clone git@gitlab.local.northwave.nl:mneikes/spo-automation.git`
 2. `pip3 install -e .`

Then, create a config file `config.ini` with the following content:

```ini
[jira]
host = https://jira.local.northwave.nl
username = spo-workflow-automation
password = (1Password)
dryrun = yes

[openai]
key = (OpenAI key)
```

The password for the spo-workflow-automation user is currently shared with Jair
and Moritz. The OpenAI key can be found by clicking the "View Code" button in
the Azure AI studio chat playground.

The **dryrun** option controls whether the code should run in passive mode, and
only log what it _would_ do (`dryrun = yes`), or whether it should actually make
changes to the Jira tickets that it processes (`dryrun = no`).

## Usage

Once installed (see Setup above), run the script like so:

```
usage: nw-spo-automation [-h] {issue,search-issues} ...

Apply automation to SPO Jira tickets

positional arguments:
  {issue,search-issues}
                        Specify the mode in which to operate
    issue               Run automation for a specific issue
    search-issues       Search for applicable issues and run automation on all of them

options:
  -h, --help            show this help message and exit
```

### Individual tickets

To run automation for a specific ticket, use the `issue` subcommand:

```
usage: nw-spo-automation issue [-h] --key KEY

options:
  -h, --help  show this help message and exit
  --key KEY   The Jira issue key
```

### Search for issues

To search for all applicable issues and run automation on all of them,
use the `search-issues` subcommand like so:

```
usage: nw-spo-automation search-issues [-h] [--limit LIMIT]

options:
  -h, --help     show this help message and exit
  --limit LIMIT  Limit the number of issues that will be handled
```

## How it works

The SPO automation currently operates in two phases:

 1. Classification
 2. Enrichment

During classification, the email content of a ticket is processed to map it to
one of a predefined set of subcategories. These subcategories are grouped into
security- and privacy-related topics.

The list of categories can be found in [./spo_automation/ticket_classifier.py](./spo_automation/ticket_classifier.py).

If there is an enrichment function defined for the subcategory, that function
will then be run with the ticket.

The enrichment functions can be found in [./spo_automation/workflows](./spo_automation/workflows). They are
grouped into security and privacy functions.

### Adding a new workflow

If necessary, expand the classifications in [./spo_automation/ticket_classifier.py](./spo_automation/ticket_classifier.py)

Then, create a new file `spo_automation/workflows/<category>/<subcategory>.py`, using
the category and _mapped_ subcategory from the ticket classifier.

The _mapped_ subcategory is the machine-friendly version of a subcategory name.
For example, the subcategory "Data Breaches (e.g., incorrectly sent email)" maps
to the mapped subcategory `data_breaches`. This mapping happens explicitly in
[./spo_automation/ticket_classifier.py](./spo_automation/ticket_classifier.py).

Your new workflow file must have at least a function with the following signature:


```python
def on_create(spo_automation, issue):
    pass
```

This function will be called with all issues that fall under your new subcategory.
Example:

```python
from spo_automation import openai_wrapper, templating

system_message = """
You are an AI assistant As an AI assistant to a Security and Privacy Officer.
Your task is to [...]

Respond only in JSON format with fields for ...

Example:
{
  "key": "value",
  # give a specific example here
}
"""

email_template = """
The AI concluded the following: {{ resp.key }}
It found the following issues:
{% for issue in resp.issues %}
 - {{ issue }}
{% endfor %}
"""

def on_create(spo_automation, issue):
    openai_instance = openai_wrapper.OpenAIWrapper(
        spo_automation.config.openai_key,
        system_message,
    )

    email_content = issue.get_field("SPO: E-mail Body")
    resp = openai_instance.create_json_completion(email_content)

    response_email = templating.render_template(
        template = email_template,
        context = {
            "resp": resp,
        }
    )


```
