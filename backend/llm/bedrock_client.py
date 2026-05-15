import json
import boto3
from botocore.exceptions import ClientError
from config import get_settings
from typing import List, Dict, Any, Optional

settings = get_settings()


class BedrockClient:
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None
        )
        self.model_id = settings.LLM_MODEL_ID

    def generate(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2048) -> str:
        messages = [{"role": "user", "content": prompt}]

        body = {
            "prompt": self._format_prompt(messages, system_prompt),
            "max_gen_len": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            response_body = json.loads(response["body"].read())
            return response_body.get("generation", "").strip()
        except ClientError as e:
            print(f"Error calling Bedrock: {e}")
            raise

    def generate_with_history(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None, max_tokens: int = 2048) -> str:
        body = {
            "prompt": self._format_prompt(messages, system_prompt),
            "max_gen_len": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            response_body = json.loads(response["body"].read())
            return response_body.get("generation", "").strip()
        except ClientError as e:
            print(f"Error calling Bedrock: {e}")
            raise

    def _format_prompt(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        formatted = ""
        if system_prompt:
            formatted += f"<|system|>\n{system_prompt}\n"
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                formatted += f"<|user|>\n{content}\n"
            elif role == "assistant":
                formatted += f"<|assistant|>\n{content}\n"
        formatted += "<|assistant|>\n"
        return formatted


bedrock_client = BedrockClient()
