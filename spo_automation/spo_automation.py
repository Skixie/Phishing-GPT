import configparser
import jira
import argparse
from dataclasses import dataclass
from spo_automation.jira_wrapper import JiraWrapper
from spo_automation import (
    ticket_classifier,
    logger,
    spo_workflow,
)
from textwrap import dedent
import traceback

logger = logger.logger

@dataclass
class SpoAutomationConfig():
    jira_host: str
    jira_user: str
    jira_password: str

    openai_key: str

    dryrun: bool = True

    @staticmethod
    def from_file(path):
        config = configparser.ConfigParser()
        config.read(path)
        return SpoAutomationConfig(
            jira_host=config['jira'].get('host'),
            jira_user=config['jira'].get('username'),
            jira_password=config['jira'].get('password'),
            openai_key=config['openai'].get('key'),
            dryrun=config['jira'].getboolean('dryrun')
        )


class SpoAutomation():

    def __init__(self, config):
        self.config = config
        self.classifier = ticket_classifier.TicketClassifier(config.openai_key)
        self.jira = JiraWrapper(
            config.jira_host,
            config.jira_user,
            config.jira_password,
            config.dryrun,
        )

    def process(self, issue):
        logger.info(f"Handling ticket {issue.key}")

        # For each new ticket, run classification
        classification = self.classifier.classify_ticket(issue)

        cl = classification

        # Format the classification and add it as a comment:
        self.jira.add_comment(
            issue.key,
            dedent(f"""
                *This issue was classified as {cl.category} - {cl.subcategory} with {cl.confidence} confidence*

                {cl.why}
                """)
        )

        # Then look up the workflow
        if not cl.mapped_subcategory:
            logger.info(f"{issue.key}: Classification was generic - not running any workflows")
            return

        try:
            func, module = spo_workflow.load_module(cl.category, cl.mapped_subcategory)
            return func(self, issue)
        except ImportError as e:
            if isinstance(e.__cause__, ModuleNotFoundError):
                logger.info(f"{issue.key}: No workflow is defined for {cl.category} - {cl.subcategory}.")
                return
            else:
                raise e

    def try_process(self, issue):
        try:
            # Add the 'spo-automation-handled' label if it isn't there yet
            if 'spo-automation-handled' not in issue.fields.labels:
                issue.fields.labels.append('spo-automation-handled')
                issue.update(
                    fields={'Labels': issue.fields.labels}
                )

            self.process(issue)
        except (Exception, AssertionError) as e:
            tb = traceback.format_exc()
            self.jira.add_comment(
                issue.key,
                f"An error occurred in the SPO-automation for this ticket:\n\n{{noformat}}\n{tb}\n{{noformat}}"  # noqa: E501
            )
        finally:
            # Any code that should happen as clean-up can go here.
            # This will be executed in the happy flow but also if there
            # has been an exception.

            # Clear SPO-automation user as assignee
            if (
                issue.fields.assignee is not None
                and issue.fields.assignee.name == self.config.jira_user
            ):
                self.jira.assign_issue(issue.key, None)


def generate_parser():
    # Usage code:
    # nw-spo-automation issue --key SPO-123456
    # nw-spo-automation search-issues --limit=20
    parser = argparse.ArgumentParser(description='Apply automation to SPO Jira tickets')

    subparsers = parser.add_subparsers(dest='command', required=True,
                                       help='Specify the mode in which to operate')

    parser_issue = subparsers.add_parser('issue', help='Run automation for a specific issue')
    parser_issue.add_argument('--key', required=True,
                            help='The Jira issue key')

    parser_search = subparsers.add_parser(
        'search-issues',
        help='Search for applicable issues and run automation on all of them')
    parser_search.add_argument('--limit', required=False, default=20, type=int,
                            help='Limit the number of issues that will be handled')

    return parser


def main():
    config = SpoAutomationConfig.from_file("config.ini")

    spo_automation = SpoAutomation(config)

    parser = generate_parser()
    args = parser.parse_args()

    if args.command == "search-issues":
        search_query = dedent("""
            project = SPO
            AND resolution = Unresolved
            AND Type = "SPO Incident"
            AND Reporter = "mailplugin"
            AND (labels is EMPTY OR labels not in ("spo-automation-handled"))
            ORDER BY updated DESC
        """)

        # Fetch tickets
        issues = spo_automation.jira.search_issues(search_query, maxResults=args.limit)
        for issue_short in issues:
            issue = spo_automation.jira.issue(issue_short.key)
            spo_automation.try_process(issue)

    elif args.command == "issue":
        issue = spo_automation.jira.issue(args.key)
        spo_automation.try_process(issue)

    else:
        raise Exception(f"Unrecognized command {args.command}")

if __name__ == "__main__":
    main()
