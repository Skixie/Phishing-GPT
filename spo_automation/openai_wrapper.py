from openai import AzureOpenAI
import json

default_completion_parameters = dict(
    temperature=0.7,
    max_tokens=800,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
)

class OpenAIWrapper():

    def __init__(
            self, openai_api_key, system_message, model="gpt-4",
            completion_parameters=default_completion_parameters
    ):
        self.instance = AzureOpenAI(
            azure_endpoint="https://instance-openai-france.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2023-07-01-preview",
            api_version="2023-12-01-preview",
            api_key=openai_api_key,
            azure_deployment="gpt-4",
        )
        self.system_message = system_message
        self.model = model
        self.completion_parameters = completion_parameters
        
    def create_completion(self, message, response_format=None):
        completion = self.instance.chat.completions.create(
            model=self.model,
            response_format=response_format,
            messages=[
                {
                    "role": "system",
                    "content": self.system_message,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            **self.completion_parameters,
        )
        return completion.choices[0].message.content

    def create_json_completion(self, message):
        completion = self.create_completion(
            message,
            response_format={"type": "json_object"})
        return json.loads(completion)
