import aiohttp
import random
from typing import Any, AsyncGenerator, Dict, List, Optional, TypeVar

from loguru import logger
from vocode.streaming.action.abstract_factory import AbstractActionFactory
from vocode.streaming.action.default_factory import DefaultActionFactory
from vocode.streaming.agent.base_agent import GeneratedResponse, RespondAgent, StreamedResponse
from vocode.streaming.models.actions import FunctionCallActionTrigger
from vocode.streaming.models.agent import AgentConfig
from vocode.streaming.models.events import Sender
from vocode.streaming.models.message import BaseMessage, BotBackchannel
from vocode.streaming.models.transcript import Message

FlowiseAgentConfigType = TypeVar("FlowiseAgentConfigType", bound=AgentConfig)


class FlowiseAgentConfig(AgentConfig):
    flowise_api_url: str
    chat_id: str


class FlowiseAgent(RespondAgent[FlowiseAgentConfigType]):
    def __init__(
        self,
        agent_config: FlowiseAgentConfigType,
        action_factory: AbstractActionFactory = DefaultActionFactory(),
        **kwargs,
    ):
        super().__init__(
            agent_config=agent_config,
            action_factory=action_factory,
            **kwargs,
        )
        self.api_url = agent_config.flowise_api_url
        self.chat_id = agent_config.chat_id

    async def send_message(self, message: str) -> str:
        payload = {
            "question": message,
            "chatId": self.chat_id,
            "overrideConfig": {},
            # "socketIOClientId": "mPVwQFURr5S1qLDHACKt"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data["text"]

    def should_backchannel(self, human_input: str) -> bool:
        return (
            not self.is_first_response()
            and not human_input.strip().endswith("?")
            and random.random() < self.agent_config.backchannel_probability
        )

    # def choose_backchannel(self) -> Optional[BotBackchannel]:
    #     backchannel = None
    #     if self.transcript is not None:
    #         last_bot_message: Optional[Message] = None
    #         for event_log in self.transcript.event_logs[::-1]:
    #             if isinstance(event_log, Message) and event_log.sender == Sender.BOT:
    #                 last_bot_message = event_log
    #                 break
    #         if last_bot_message and last_bot_message.text.strip().endswith("?"):
    #             return BotBackchannel(text=self.post_question_bot_backchannel_randomizer())
    #     return backchannel

    async def generate_response(
        self,
        human_input: str,
        conversation_id: str,
        is_interrupt: bool = False,
        bot_was_in_medias_res: bool = False,
    ) -> AsyncGenerator[GeneratedResponse, None]:
        assert self.transcript is not None
        print(human_input)

        # backchannelled = "false"
        # backchannel: Optional[BotBackchannel] = None
        # if (
        #     self.agent_config.use_backchannels
        #     and not bot_was_in_medias_res
        #     and self.should_backchannel(human_input)
        # ):
        #     backchannel = self.choose_backchannel()
        # elif self.agent_config.first_response_filler_message and self.is_first_response():
        #     backchannel = BotBackchannel(text=self.agent_config.first_response_filler_message)

        # if backchannel is not None:
        #     yield GeneratedResponse(
        #         message=backchannel,
        #         is_interruptible=True,
        #     )
        #     backchannelled = "true"


        response_text = await self.send_message(human_input)
        print(response_text)

        yield GeneratedResponse(
            message=BaseMessage(text=response_text),
            is_interruptible=True,
        )

    async def terminate(self):
        return await super().terminate()