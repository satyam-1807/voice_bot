import asyncio
import signal
import uuid

from pydantic_settings import BaseSettings, SettingsConfigDict

from vocode.helpers import create_streaming_microphone_input_and_speaker_output
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import AzureSynthesizerConfig
from vocode.streaming.models.transcriber import (
    DeepgramTranscriberConfig,
    PunctuationEndpointingConfig,
)
from vocode.streaming.streaming_conversation import StreamingConversation
from vocode.streaming.synthesizer.azure_synthesizer import AzureSynthesizer
from vocode.streaming.transcriber.deepgram_transcriber import DeepgramTranscriber
from flowise_agent import FlowiseAgent, FlowiseAgentConfig

# configure_pretty_logging()


class Settings(BaseSettings):
    """
    Settings for the streaming conversation quickstart.
    These parameters can be configured with environment variables.
    """

    openai_api_key: str = "sk-proj-8dMh435vAkkx70BD3zP1T3BlbkFJJSkuEushVxuEQ5PYAkkw"
    azure_speech_key: str = "d31436658f234e619bab457ccbb8bcf1"
    deepgram_api_key: str = "92c1f9b1e9e58fadd18cd5d646346499b59d8959"

    azure_speech_region: str = "eastus"

    # This means a .env file can be used to overload these settings
    # ex: "OPENAI_API_KEY=my_key" will set openai_api_key over the default above
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


async def main():
    (
        microphone_input,
        speaker_output,
    ) = create_streaming_microphone_input_and_speaker_output(
        use_default_devices=True,
    )
    synconfig = AzureSynthesizerConfig.from_output_device(speaker_output)
    synconfig.voice_name = "en-GB-RyanNeural"
    synconfig.language_code = "en-GB"
    conversation = StreamingConversation(
        output_device=speaker_output,
        transcriber=DeepgramTranscriber(
            DeepgramTranscriberConfig.from_input_device(
                microphone_input,
                endpointing_config=PunctuationEndpointingConfig(),
                api_key=settings.deepgram_api_key,
            ),
        ),
        agent=FlowiseAgent(  # Use FlowiseAgent
            FlowiseAgentConfig(
                flowise_api_url="https://dev-llm.deeptalk.work/api/v1/prediction/c7686ede-9366-4d66-967c-7b56a790afe4",
                chat_id=str(uuid.uuid4())
            )
        ),
        synthesizer=AzureSynthesizer(
            synconfig,
            azure_speech_key=settings.azure_speech_key,
            azure_speech_region=settings.azure_speech_region,
        ),
    )
    await conversation.start()
    print("Conversation started, press Ctrl+C to end")
    signal.signal(signal.SIGINT, lambda _0, _1: asyncio.create_task(conversation.terminate()))
    while conversation.is_active():
        chunk = await microphone_input.get_audio()
        conversation.receive_audio(chunk)


if __name__ == "__main__":
    asyncio.run(main())