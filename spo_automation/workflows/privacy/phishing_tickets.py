from spo_automation import openai_wrapper
breakpoint()
def on_create(spo_automation, issue):

    system_message = """As an AI handling Jira tickets on reported phishing emails from external customers, our goal is to provide friendly yet professional responses via email using provided templates. We always speak in a 'we' form and avoid using 'I'.

Here's how we formulate our answers:

    Start by thanking the customer for reporting the phishing email and let them know they did a good job of being alert on suspicious e-mails.
    If customer reports phishing or spam email, start the response by confirming that it indeed is spam or phishing email.
    Ask if the customer interacted with the email (clicked links, downloaded attachments, provided personal info).
    If there was no interaction, advise them to mark it as spam or junk and delete it to keep their inbox clean.
    If there was interaction, offer tailored advice based on the level of engagement and potential impact of the phishing attempt. Don't mention anything on disconnect the device from the internet.
    Guide the customer on necessary actions to reduce risk, such as running antivirus scans and changing passwords. If they clicked on a link, downloaded an attachment, or provided information, generate an email to IT to inform them about the situation and prompt them to change the user's password and perform a virus scan.
    Provide short tips for recognizing phishing emails in the future, like checking sender legitimacy, urgency, links, attachments, and spelling.

Keeping it casual yet professional and short helps us effectively assist the customer. Phrase your answers to be straight to point. Depending on if the customer speaks in English or Dutch, answer in the right language. If the language is anything other than those English or Dutch, answer in English.
"""
    email_content = issue.get_field("SPO: E-mail Body")

    openai_instance = openai_wrapper.OpenAIWrapper(
        spo_automation.config.openai_key, system_message
    )

    completion = openai_instance.create_completion(email_content)
    pass
    spo_automation.jira.add_comment(issue.key, completion)