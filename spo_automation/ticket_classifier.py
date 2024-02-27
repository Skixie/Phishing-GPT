from enum import Enum, auto
import json
from textwrap import dedent
from dataclasses import dataclass

from spo_automation import openai_wrapper

# This mapping defines the classifications that the model should use to classify
# the tickets. Classifications are divided into security-related and
# privacy-related subcategories, and each subcategory maps to a stable name.
# While we can freely change the human-readable subcategory names, the stable
# names shouldn't change.
classifications = {
    "Security": {
        "Phishing e-mails": "phishing_emails",
        "Resolution of ESET disabled alarms by the SPO": "eset_disabled_alarms",
        "Opening .MSG files": "opening_msg_files",
        "Responding to responsible disclosure reports": "responding_to_responsible_disclosure_reports",
        "Spam e-mails": "spam_emails",
        "Outlook rule detected": "outlook_rule_detected",
        "Physical break-in": "physical_break_in",
        "Lost or stolen devices, data carriers and/or papers": "lost_or_stolen_devices_data_carriers_papers",
        "Malware infection": "malware_infection",
    },
    "Privacy": {
        "Estimating country risk for Working Abroad requests": "estimating_country_risk_for_working_abroad",
        "Data Breaches (e.g., incorrectly sent email)": "data_breaches",
        "Handling a Data Subject's Request": "handling_a_data_subjects_request",
        "Privacy statement review": "privacy_statement_review",
        "Filling in the databreach tab": "filling_in_the_databreach_tab",
        "Is a DPIA required?": "is_a_dpia_required",
        "Reviewing DPA's / Verwerkersovereenkomst": "reviewing_dpas",
        "Controller or Processor?": "controller_or_processor",
        "Stappenplan Datalek Beoordeling": "stappenplan_datalek_beoordeling",
    },
}


list_of_security_subcategories = "\n".join([
    "  • " + subcategory for subcategory in classifications["Security"].keys()
])

list_of_privacy_subcategories = "\n".join([
    "  • " + subcategory for subcategory in classifications["Privacy"].keys()
])

system_message = f"""
As an AI assistant to a Security and Privacy Officer,
your task is to classify incoming email messages into relevant categories.
Only classify tickets in the two major classifications 'Security' and 'Privacy'. Use
the following guidelines:

Security-Related Queries:
- Classify as one of the following:
{list_of_security_subcategories}
  • If none fit, classify as "Generic Security".

Privacy-Related Queries:
- Classify as one of the following:
{list_of_privacy_subcategories}
  • If none fit, classify as "Generic Privacy".

Respond only in JSON format with fields for 'category', 'subcategory', 'why'
(explanation for your classification), and 'confidence' (your confidence level
in the classification).

Example:
{"{"}
  "category": "Security",
  "subcategory": "Phishing e-mails",
  "why": "The email contains characteristics of a phishing attempt, such as...",
  "confidence": "High"
{"}"}
"""

@dataclass
class TicketClassification():
    category: str
    subcategory: str
    mapped_subcategory: str
    confidence: str
    why: str

class TicketClassifier():

    def __init__(self, openai_api_key):
        self.openai_instance = openai_wrapper.OpenAIWrapper(openai_api_key, system_message)


    def classify_ticket(self, issue):
        email_content = issue.get_field("SPO: E-mail Body")

        cljson = self.openai_instance.create_json_completion(email_content)

        category = cljson["category"]
        # These are the two major classifications that we expect
        if category == "Security":
            mapped_subcategory = classifications[category].get(
                cljson["subcategory"], "generic_security"
            )
        elif category == "Privacy":
            mapped_subcategory = classifications[category].get(
                cljson["subcategory"], "generic_privacy"
            )
        else:
            # Otherwise raise an exception
            raise Exception(f"unexpected major classification {cljson['category']}")

        return TicketClassification(
            category=cljson["category"],
            subcategory=cljson["subcategory"],
            mapped_subcategory = mapped_subcategory,
            why=cljson["why"],
            confidence=cljson["confidence"],
        )
