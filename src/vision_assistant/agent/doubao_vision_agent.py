import base64
import io
from PIL import Image
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Optional

from vision_assistant.types import (
    AppConfig,
    AnalysisResult,
    VisionAgent,
    ConversationRound,
)
from vision_assistant.agent.conversation_memory import ConversationMemory


class DoubaoVisionAgent(VisionAgent):
    """Vision analysis agent using Doubao multi-modal LLM via OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name
        self._llm: Optional[ChatOpenAI] = None
        self._current_config: Optional[AppConfig] = None

        # Initialize LLM on creation
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialize the LLM client."""
        self._llm = ChatOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            temperature=0.7,
            max_tokens=1024,
        )

    def _encode_image(
        self,
        image: Image.Image,
        config: AppConfig,
    ) -> str:
        """Resize, compress, and encode image to base64."""
        # Resize to target dimensions while maintaining aspect ratio
        image.thumbnail((config.target_width, config.target_height), Image.Resampling.LANCZOS)

        # Save as JPEG with specified quality
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=config.jpeg_quality)
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _build_system_prompt(
        self,
        config: AppConfig,
        history: list[ConversationRound],
        user_message: str | None = None,
    ) -> str:
        """Build the complete system prompt.

        Args:
            config: Application configuration containing persona and target
            history: Previous conversation rounds
            user_message: Optional user-initiated message from manual input
                when user double-clicks the character. Added to prompt as user input.

        Returns:
            Formatted system prompt string
        """
        prompt_parts = []

        # Add persona
        prompt_parts.append(config.llm_system_prompt.strip())
        prompt_parts.append("")

        # Add monitoring instruction
        if user_message is None:
            # Automatic monitoring mode
            prompt_parts.append(
                f"Your task: Monitor the screen for this behavior: {config.monitoring_target.strip()}"
            )
            prompt_parts.append("")
            prompt_parts.append("Analyze the screenshot and respond in this format:")
            prompt_parts.append("DETECTED: [yes/no]")
            prompt_parts.append("MESSAGE: [your message based on your persona]")
            prompt_parts.append("")
            prompt_parts.append(
                "If the target behavior is detected, you must output 'DETECTED: yes' "
                "and provide a message."
            )
            prompt_parts.append(
                "If the target behavior is not detected, output 'DETECTED: no' and your response."
            )
        else:
            # User-initiated conversation mode
            prompt_parts.append(
                "The user has sent you a message directly. Respond to the user's message "
                "according to your persona."
            )

        # Add history if any - use ConversationMemory's formatting
        if history:
            # Create a temporary ConversationMemory to reuse its formatting logic
            temp_memory = ConversationMemory(max_turns=len(history))
            for round_obj in history:
                temp_memory.add_round(
                    timestamp=round_obj.timestamp,
                    detected_behavior=round_obj.detected_behavior,
                    message=round_obj.message
                )
            history_text = temp_memory.format_for_prompt()
            if history_text:
                prompt_parts.append("")
                prompt_parts.append(history_text)

        # Add user message if provided
        if user_message is not None:
            prompt_parts.append("")
            prompt_parts.append(f"User: {user_message}")
            prompt_parts.append("Assistant:")

        return "\n".join(prompt_parts)

    def _parse_response(
        self,
        response_text: str,
        force_detected_false: bool = False,
    ) -> AnalysisResult:
        """Parse raw LLM response into structured result.

        Args:
            response_text: Raw response text from LLM
            force_detected_false: If True, force detected to False regardless of
                parsed result. This is used when we have a user-initiated message
                so we skip automatic detection.

        Returns:
            Structured AnalysisResult
        """
        detected = False
        message = ""
        response_text = response_text.strip()

        # Parse for DETECTED and MESSAGE lines
        lines = response_text.splitlines()
        for line in lines:
            line = line.strip()
            if line.lower().startswith('detected:'):
                value = line.split(':', 1)[1].strip().lower()
                detected = value in ['yes', 'true', 'y']
            elif line.lower().startswith('message:'):
                message = line.split(':', 1)[1].strip()

        # If no message found, take everything after detected line as fallback
        if not message:
            found_detected = False
            message_parts = []
            for line in lines:
                if not found_detected and line.lower().startswith('detected:'):
                    found_detected = True
                    continue
                if found_detected and line.strip():
                    message_parts.append(line.strip())
            if message_parts:
                message = ' '.join(message_parts)

        # If we have a user-initiated message, force detected to False
        # This skips the automatic detection behavior
        if force_detected_false:
            detected = False
            # For user-initiated messages, the model responds conversationally
            # without DETECTED:/MESSAGE: headers. Use the entire response as message.
            if not message:
                message = response_text

        return AnalysisResult(
            detected=detected,
            message=message,
            raw_analysis=response_text,
        )

    def analyze_screenshot(
        self,
        image: Image.Image | None,
        config: AppConfig,
        history: list[ConversationRound],
        user_message: str | None = None,
    ) -> AnalysisResult:
        """Analyze a screenshot and return the result.

        Args:
            image: Current screenshot image (None for text-only user messages)
            config: Application configuration
            history: Previous conversation history
            user_message: Optional user-initiated message from manual input
                when user double-clicks the character. If provided, this message
                is added to the prompt and we skip automatic detection.

        Returns:
            Analysis result with detected flag and message
        """
        if self._llm is None:
            self._init_llm()

        # Build prompt inline
        system_prompt = self._build_system_prompt(config, history, user_message)

        # Create messages - text-only when user_message is provided (no screenshot)
        if user_message is not None:
            # User-initiated conversation: text only, no screenshot
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
        else:
            # Automatic monitoring: include screenshot
            base64_image = self._encode_image(image.copy(), config)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Here is the current screenshot:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                )
            ]

        # Call LLM
        response = self._llm.invoke(messages)
        response_text = str(response.content)

        # Parse response inline
        # If we have a user-initiated message, force detected to False
        force_detected_false = user_message is not None
        result = self._parse_response(response_text, force_detected_false)

        return result

    def update_config(self, config: AppConfig) -> None:
        """Update agent with new configuration."""
        self._current_config = config
        # No need to reinitialize LLM on config change, only API/model changes require that
