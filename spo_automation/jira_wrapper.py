import jira

from soc_jira_tools import JiraCustomFieldTranslation
# from spo_automation.logger import logger as dryrun_logger
import logging

dryrun_logger = logging.getLogger(__name__)
dryrun_logger.setLevel(logging.DEBUG)
dryrun_logger.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - DRYRUN - %(issue_key)s - %(message)s"
))
dryrun_logger.addHandler(handler)

dryrun_logger.dryrun_info = lambda issue_key, msg: dryrun_logger.info(msg, extra={'issue_key': issue_key})
dryrun_logger.dryrun_debug = lambda issue_key, msg: dryrun_logger.debug(msg, extra={'issue_key': issue_key})

# This is a wrapper class around a Jira instance.
# The wrapper can be configured in dryrun mode,
# in which case it won't make any destructive changes.
class JiraWrapper:
    def __init__(self, jira_host, jira_user, jira_password, dryrun):
        self._actual_jira = jira.JIRA(
            server=jira_host,
            basic_auth=(jira_user, jira_password),
        )
        # Store the connection parameters separately so that we can make a POST
        # request to send an email
        self._jira_host = jira_host
        self._jira_user = jira_user
        self._jira_password = jira_password

        self._jira_custom_field_translation = JiraCustomFieldTranslation(self._actual_jira)

        self.dryrun = dryrun

        # Non-destructive functions:
        self.transitions = self._actual_jira.transitions
        self.search_issues = self._actual_jira.search_issues

    def issue(self, issue_key):
        actual_issue = self._actual_jira.issue(issue_key, expand="names")
        return JiraIssueWrapper(self, actual_issue)

    def comment(self, issue_key, comment_id):
        try:
            actual_comment = self._actual_jira.comment(issue_key, comment_id)
            return JiraCommentWrapper(self, issue_key, actual_comment)
        except jira.JIRAError:
            if self.dryrun:
                # In a dryrun mode there might be cases where we request
                # a non-existent comment
                return JiraCommentWrapper(self, issue_key, dummy_data=dict(
                    id="123456",
                    body="",
                    created="2022-10-02T08:12:17.961+0200",
                    updated="2022-10-02T08:12:17.961+0200",
                ))
            else:
                raise

    def add_comment(self, issue_key, body):
        if self.dryrun:
            dryrun_logger.dryrun_info(issue_key, "Adding comment")
            for line in body.splitlines():
                dryrun_logger.dryrun_debug(issue_key, f"> {line}")
            return JiraCommentWrapper(self, issue_key, dummy_data=dict(
                id="123456",
                body=body,
                created="2022-10-02T08:12:17.961+0200",
                updated="2022-10-02T08:12:17.961+0200",
            ))
        else:
            actual_comment = self._actual_jira.add_comment(issue_key, body)
            return JiraCommentWrapper(self, issue_key, actual_comment)

    def assign_issue(self, issue, assignee):
        if self.dryrun:
            dryrun_logger.dryrun_info(issue, f"Assigning to {assignee}")
            return True
        else:
            return self._actual_jira.assign_issue(issue, assignee)

    def transition_issue(self, issue, transition, fields=None, comment=None):
        if fields:
            # Convert custom field names to custom field IDs
            fields = self._jira_custom_field_translation.edit_convert_name_to_id(
                issue, fields
            )

        if self.dryrun:
            dryrun_logger.dryrun_info(
                issue, f"Transitioning to {transition} with fields {fields} and comment {comment}")
        else:
            return self._actual_jira.transition_issue(issue, transition, fields, comment)


class JiraIssueWrapper:
    def __init__(self, jira_wrapper, actual_issue=None, dummy_data=None):
        self._jira = jira_wrapper
        self._actual_issue = actual_issue
        if actual_issue:
            # We make custom fields available by their human-readable name
            self.fields = self._actual_issue.fields
            for id, name in self._actual_issue.names.__dict__.items():
                self.fields.__dict__[name] = self.fields.__dict__[id]

            self.key = self._actual_issue.key
            self.id = self._actual_issue.id
        else:
            assert jira_wrapper.dryrun, "Unless we're running in dryrun mode, an actual issue must be provided."
            jira.resources.dict2resource(dummy_data or dict(), self)

    def get_field(self, name: str):
        if self._actual_issue:
            field_id = self._jira._jira_custom_field_translation.get_convert_name_to_id(name)
            if hasattr(self._actual_issue.fields, field_id):
                return self._actual_issue.get_field(field_id)
            else:
                return None

    def update(self, fields=None, **fieldargs):
        # Convert custom field names to custom field IDs
        converted_fields = self._jira._jira_custom_field_translation.edit_convert_name_to_id(
            self.key, fields
        )

        if self._jira.dryrun:
            # Use the human-readable name in the log, rather than the translated fields
            dryrun_logger.dryrun_info(self.key, f"Updating fields {fields} {fieldargs}")
        else:
            return self._actual_issue.update(converted_fields, **fieldargs)


class JiraCommentWrapper:
    def __init__(self, jira_wrapper, issue_key, actual_comment=None, dummy_data=None):
        self._jira = jira_wrapper
        self._actual_comment = actual_comment
        self.issue_key = issue_key
        if actual_comment:
            self.id = self._actual_comment.id
            self.body = self._actual_comment.body
            self.created = self._actual_comment.created
            self.updated = self._actual_comment.updated
            self.author = self._actual_comment.author
            self.updateAuthor = self._actual_comment.updateAuthor
        else:
            assert jira_wrapper.dryrun, "Unless we're running in dryrun mode, an actual comment must be provided."
            jira.resources.dict2resource(dummy_data or dict(), self)

    def update(self, body):
        if self._jira.dryrun:
            dryrun_logger.dryrun_info(self.issue_key, f"Updating body of comment {self.id}:")
            for line in body.splitlines():
                dryrun_logger.dryrun_debug(self.issue_key, f"> {line}")
        else:
            return self._actual_comment.update(body=body)
