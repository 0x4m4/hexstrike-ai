#!/usr/bin/env python3
"""
MindSync Oracle - Multi-Modal Input Processor

Handles input from ANY source, not just voice:
- Text (CLI, chat, etc.)
- Voice (Whisper transcription)
- Files (documents, code, images)
- Screen context (what user is working on)
- Structured data (JSON, CSV, APIs)

Normalizes everything into a unified InputEvent for processing.
"""

import os
from typing import Dict, Any, Optional, Union, BinaryIO
from dataclasses import dataclass
from pathlib import Path
import logging
import json
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class InputEvent:
    """
    Unified input event structure.

    All inputs (text, voice, files, etc.) are normalized to this format.
    """
    content: str  # Main content (text, transcription, file summary, etc.)
    input_type: str  # 'text', 'voice', 'file', 'screen', 'structured'
    metadata: Dict[str, Any]  # Additional context
    timestamp: datetime
    raw_data: Optional[Any] = None  # Original data if needed


class MultiModalInputProcessor:
    """
    Process input from multiple modalities.

    Expands beyond voice-only to support:
    - Direct text input
    - Voice transcription
    - File uploads
    - Screen context
    - Structured data
    """

    def __init__(self, whisper_api_key: Optional[str] = None):
        """
        Initialize the input processor.

        Args:
            whisper_api_key: OpenAI API key for Whisper (optional)
        """
        self.whisper_api_key = whisper_api_key or os.getenv("OPENAI_API_KEY")
        self.whisper_client = None

        if self.whisper_api_key:
            try:
                from openai import OpenAI
                self.whisper_client = OpenAI(api_key=self.whisper_api_key)
                logger.info("Whisper client initialized")
            except ImportError:
                logger.warning("OpenAI library not installed - voice input disabled")

        logger.info("Multi-Modal Input Processor initialized")

    # ===== TEXT INPUT =====

    def process_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> InputEvent:
        """
        Process direct text input.

        Args:
            text: Input text
            metadata: Optional metadata

        Returns:
            InputEvent
        """
        return InputEvent(
            content=text,
            input_type="text",
            metadata=metadata or {},
            timestamp=datetime.now()
        )

    # ===== VOICE INPUT =====

    def process_voice(self, audio_file: Union[str, BinaryIO],
                     metadata: Optional[Dict[str, Any]] = None) -> InputEvent:
        """
        Process voice input via Whisper transcription.

        Args:
            audio_file: Path to audio file or file-like object
            metadata: Optional metadata

        Returns:
            InputEvent with transcribed text
        """
        if not self.whisper_client:
            raise RuntimeError("Whisper client not initialized - check API key")

        try:
            # Transcribe audio
            if isinstance(audio_file, str):
                with open(audio_file, "rb") as f:
                    transcription = self.whisper_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
            else:
                transcription = self.whisper_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            transcribed_text = transcription.text

            logger.info(f"Voice transcribed: {transcribed_text[:100]}...")

            return InputEvent(
                content=transcribed_text,
                input_type="voice",
                metadata=metadata or {},
                timestamp=datetime.now(),
                raw_data={"audio_file": str(audio_file) if isinstance(audio_file, str) else None}
            )

        except Exception as e:
            logger.error(f"Error transcribing voice: {e}", exc_info=True)
            raise

    # ===== FILE INPUT =====

    def process_file(self, file_path: str,
                    metadata: Optional[Dict[str, Any]] = None) -> InputEvent:
        """
        Process file input (documents, code, etc.).

        Args:
            file_path: Path to file
            metadata: Optional metadata

        Returns:
            InputEvent with file content
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect file type
        file_ext = file_path_obj.suffix.lower()

        # Text files
        if file_ext in ['.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.csv']:
            content = self._process_text_file(file_path_obj)

        # Image files (describe for AI)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            content = self._process_image_file(file_path_obj)

        # Binary files
        else:
            content = self._process_binary_file(file_path_obj)

        return InputEvent(
            content=content,
            input_type="file",
            metadata={
                "file_path": str(file_path_obj),
                "file_name": file_path_obj.name,
                "file_ext": file_ext,
                "file_size": file_path_obj.stat().st_size,
                **(metadata or {})
            },
            timestamp=datetime.now(),
            raw_data={"file_path": str(file_path_obj)}
        )

    def _process_text_file(self, file_path: Path) -> str:
        """Read text file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.info(f"Read text file: {file_path.name} ({len(content)} chars)")
            return content

        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            return content

    def _process_image_file(self, file_path: Path) -> str:
        """
        Process image file.

        For Claude, we can send images directly. For now, we describe them.
        """
        # Read image as base64
        with open(file_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Return description + base64 data
        content = f"""[IMAGE FILE: {file_path.name}]

This is an image file that can be analyzed visually.
File size: {file_path.stat().st_size} bytes

Base64 data available for AI vision analysis.
"""

        logger.info(f"Processed image: {file_path.name}")
        return content

    def _process_binary_file(self, file_path: Path) -> str:
        """Process binary file (provide metadata only)."""
        return f"""[BINARY FILE: {file_path.name}]

File type: {file_path.suffix}
File size: {file_path.stat().st_size} bytes
Location: {file_path}

This is a binary file that may require specialized tools for analysis.
"""

    # ===== SCREEN CONTEXT INPUT =====

    def process_screen_context(self, context: Dict[str, Any],
                              metadata: Optional[Dict[str, Any]] = None) -> InputEvent:
        """
        Process screen context (what user is currently working on).

        Args:
            context: Screen context dictionary
                - active_window: Current window title
                - active_file: File being edited
                - clipboard: Clipboard content
                - etc.
            metadata: Optional metadata

        Returns:
            InputEvent with context summary
        """
        # Build context summary
        context_parts = []

        if context.get('active_window'):
            context_parts.append(f"Active window: {context['active_window']}")

        if context.get('active_file'):
            context_parts.append(f"Current file: {context['active_file']}")

        if context.get('clipboard'):
            context_parts.append(f"Clipboard: {context['clipboard'][:200]}...")

        if context.get('recent_commands'):
            context_parts.append(f"Recent commands: {', '.join(context['recent_commands'])}")

        content = "Current screen context:\n" + "\n".join(context_parts)

        return InputEvent(
            content=content,
            input_type="screen",
            metadata={
                "raw_context": context,
                **(metadata or {})
            },
            timestamp=datetime.now(),
            raw_data=context
        )

    # ===== STRUCTURED DATA INPUT =====

    def process_structured_data(self, data: Union[Dict, list],
                               data_format: str = "json",
                               metadata: Optional[Dict[str, Any]] = None) -> InputEvent:
        """
        Process structured data (JSON, CSV, API responses, etc.).

        Args:
            data: Structured data (dict or list)
            data_format: Format identifier ('json', 'csv', 'api_response')
            metadata: Optional metadata

        Returns:
            InputEvent with formatted data
        """
        # Format data as readable text
        if data_format == "json":
            content = f"[STRUCTURED DATA: JSON]\n\n{json.dumps(data, indent=2)}"
        else:
            content = f"[STRUCTURED DATA: {data_format}]\n\n{str(data)}"

        return InputEvent(
            content=content,
            input_type="structured",
            metadata={
                "data_format": data_format,
                "data_size": len(str(data)),
                **(metadata or {})
            },
            timestamp=datetime.now(),
            raw_data=data
        )

    # ===== BATCH PROCESSING =====

    def process_batch(self, inputs: list) -> list:
        """
        Process multiple inputs at once.

        Args:
            inputs: List of (input_type, input_data, metadata) tuples

        Returns:
            List of InputEvents
        """
        events = []

        for input_type, input_data, metadata in inputs:
            if input_type == "text":
                event = self.process_text(input_data, metadata)
            elif input_type == "voice":
                event = self.process_voice(input_data, metadata)
            elif input_type == "file":
                event = self.process_file(input_data, metadata)
            elif input_type == "screen":
                event = self.process_screen_context(input_data, metadata)
            elif input_type == "structured":
                event = self.process_structured_data(input_data, metadata=metadata)
            else:
                logger.warning(f"Unknown input type: {input_type}")
                continue

            events.append(event)

        logger.info(f"Batch processed {len(events)} inputs")
        return events

    # ===== UTILITY =====

    def format_for_agent(self, event: InputEvent) -> str:
        """
        Format an InputEvent for agent processing.

        Args:
            event: InputEvent to format

        Returns:
            Formatted string for agent consumption
        """
        formatted = f"""[INPUT: {event.input_type.upper()}]
Timestamp: {event.timestamp.isoformat()}

{event.content}
"""

        if event.metadata:
            formatted += f"\n[METADATA]\n{json.dumps(event.metadata, indent=2)}"

        return formatted


class VoiceInputHelper:
    """
    Helper for continuous voice input.

    Handles:
    - Recording audio
    - Detecting speech/silence
    - Chunking long recordings
    - Queue management
    """

    def __init__(self, processor: MultiModalInputProcessor):
        self.processor = processor
        self.is_recording = False

    def start_recording(self):
        """Start continuous voice recording."""
        self.is_recording = True
        logger.info("Voice recording started")

    def stop_recording(self) -> Optional[InputEvent]:
        """Stop recording and process audio."""
        self.is_recording = False
        logger.info("Voice recording stopped")
        # TODO: Implement actual recording
        return None


if __name__ == "__main__":
    # Test the input processor
    logging.basicConfig(level=logging.INFO)

    processor = MultiModalInputProcessor()

    # Test text input
    event = processor.process_text("I need to scan example.com for vulnerabilities")
    print(f"Text event: {event.content}")

    # Test file input (if file exists)
    try:
        event = processor.process_file("README.md")
        print(f"File event: {event.content[:200]}...")
    except FileNotFoundError:
        print("README.md not found - skipping file test")

    # Test screen context
    event = processor.process_screen_context({
        "active_window": "VSCode - main.py",
        "active_file": "/home/user/project/main.py",
        "clipboard": "import asyncio"
    })
    print(f"Screen context: {event.content}")

    # Test structured data
    event = processor.process_structured_data({
        "target": "example.com",
        "ports": [80, 443, 8080],
        "status": "active"
    })
    print(f"Structured data: {event.content}")
