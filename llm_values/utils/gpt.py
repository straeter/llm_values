import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, TypedDict, Optional

import anthropic
from decouple import config
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from openai import OpenAI

logging.basicConfig(level=logging.WARNING)


class GptMessage(TypedDict):
    role: str
    name: Optional[str]
    content: str


class ChatCompletion(TypedDict):
    model: str
    conversation: List[GptMessage]


class GPT:
    def __init__(self):
        self.executor = ThreadPoolExecutor()
        self.completion_log: List[ChatCompletion] = []
        self.listeners = set()
        self.openai = OpenAI(api_key=config("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")))
        self.mistral = MistralClient(api_key=config("MISTRAL_API_KEY", os.getenv("MISTRAL_API_KEY")))
        self.anthropic = anthropic.Anthropic(api_key=config("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")))

    def get_completion_log(self) -> List[ChatCompletion]:
        return self.completion_log

    async def log_response(self, response, model, conversation):
        logging.info(f"Response {response}")

        # Add the outgoing message and the incoming response to the completion log.
        self.completion_log.append(
            {"model": model, "conversation": conversation + [response]}
        )

        # Notify listeners
        for listener in self.listeners:
            await listener(self.completion_log[-1])

    def create_streamed_conversation_completion(
            self, model, conversation: List[GptMessage], json_mode: bool
    ):
        chat_stream = self._create_conversation_completion(
            model, conversation, json_mode, True
        )

        def get_streamed_ai_response(stream):
            full_response = ""
            for chunk in stream:
                res = chunk.choices[0].delta.content
                if res:
                    full_response += res
                    yield res

        return get_streamed_ai_response(chat_stream)

    async def create_conversation_completion(
            self, model, conversation: List[GptMessage], json_mode: bool, **kwargs
    ):
        loop = asyncio.get_event_loop()
        chat_completion = await loop.run_in_executor(
            self.executor,
            self._create_conversation_completion,
            model,
            conversation,
            json_mode,
            **kwargs
        )
        response = chat_completion.choices[0].message
        await self.log_response(response, model, conversation)

        return response

    def _create_conversation_completion(
            self, model: str, conversation: list, json_mode: bool, stream: bool = False, **kwargs
    ):
        logging.info(f"Creating chat completion for conversation {conversation}")

        try:
            if model.lower().startswith("gpt"):
                if model == "gpt-4":
                    actual_model = "gpt-4-0125-preview"
                elif model == "gpt-4o":
                    actual_model = "gpt-4o-2024-05-13"
                elif model == "gpt-3.5":
                    actual_model = "gpt-3.5-turbo-0125"
                else:
                    actual_model = model

                logging.info(f"Using openai for: {conversation}")
                chat_completion = self.openai.chat.completions.create(
                    messages=conversation,
                    model=actual_model,  # gpt-4-turbo-preview, gpt-4-1106-preview, gpt-4-vision-preview, gpt-4
                    stream=stream,
                    response_format={"type": "json_object" if json_mode else "text"},
                    **kwargs
                )

            elif model.lower().startswith("claude"):

                if not stream:
                    chat_completion = self.anthropic.messages.create(
                        model=model,
                        messages=conversation,
                        **kwargs
                    )
                else:
                    chat_completion = self.anthropic.messages.stream(
                        messages=conversation,
                        model=model,
                        **kwargs
                    )

            elif model.lower().startswith("mistral"):
                logging.info(f"Using mistral for: {conversation}")
                messages = []
                for message in conversation:
                    if isinstance(message, dict):
                        messages.append(
                            ChatMessage(
                                role=message["role"], content=message["content"]
                            )
                        )
                    else:
                        messages.append(
                            ChatMessage(role=message.role, content=message.content)
                        )

                chat_call = self.mistral.chat_stream if stream else self.mistral.chat
                chat_completion = chat_call(
                    model=model,  # mistral-tiny, mistral-small, mistral-medium
                    messages=messages,
                    safe_mode=True,
                    **kwargs
                )

            else:
                raise Exception(f"Unknown model: {model}")

            logging.info(f"Chat completion {chat_completion}")

            return chat_completion

        except Exception as e:
            logging.error(f"Error during chat completion: {e}")
            raise

    def chat(self, prompt: str, model: str, json_mode: bool = False):
        conversation = [{"role": "user", "content": prompt}]
        response = self._create_conversation_completion(model, conversation, json_mode=json_mode)
        return response.choices[0].message.content
