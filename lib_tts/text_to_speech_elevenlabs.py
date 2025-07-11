import asyncio
import base64
import io
import re
from pydub import AudioSegment
from elevenlabs.client import AsyncElevenLabs
from lib_infrastructure.dispatcher import (
    Dispatcher, Message,
    MessageHeader, MessageType,
)

class TextToSpeechElevenLabs:
    def __init__(self, guid, dispatcher: Dispatcher, api_key, voice_id="21m00Tcm4TlvDq8ikWAM"):
        self.guid = guid 
        self.dispatcher = dispatcher
        self.api_key = api_key
        self.voice_id = voice_id
        self.send_buffer_event = True
        
        # Initialize async ElevenLabs client
        self.client = AsyncElevenLabs(api_key=self.api_key)
        
        # Buffer for collecting words
        self.word_buffer = ""
        self.buffer_timer = None
        self.min_buffer_size = 10  # Increased minimum words
        self.max_buffer_time = 2.5  # Reduced timer
        self.is_processing = False
        
        # Audio queue to prevent overlapping
        self.audio_queue = asyncio.Queue()
        self.queue_processor_running = False
        
    async def start_audio_queue_processor(self):
        """Start the audio queue processor if not already running"""
        if not self.queue_processor_running:
            self.queue_processor_running = True
            asyncio.create_task(self._process_audio_queue())
    
    async def _process_audio_queue(self):
        """Process audio queue one at a time to prevent overlaps"""
        while True:
            try:
                # Get next audio task from queue
                text_to_convert = await self.audio_queue.get()
                
                if text_to_convert is None:  # Shutdown signal
                    break
                    
                # Convert to audio (this takes time)
                await self._convert_to_audio_sync(text_to_convert)
                
                # Mark task as done
                self.audio_queue.task_done()
                
                # Small delay to prevent rapid-fire audio
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Audio queue processor error: {e}")
    
    async def _convert_to_audio_sync(self, text: str):
        """Synchronous audio conversion (called by queue processor)"""
        text = text.replace('*', '').strip()
        if not text:
            return
            
        try:
            print(f"🎤 Converting to audio: '{text}'")
            audio_generator = await self.client.generate(
                text=text,
                voice=self.voice_id,
                model="eleven_multilingual_v2",
                stream=True
            )
            
            # Process chunks as they arrive
            audio_chunks = []
            async for chunk in audio_generator:
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
            
            # Combine all chunks and convert format
            if audio_chunks:
                mp3_data = b''.join(audio_chunks)
                converted_audio = await self.convert_audio_format(mp3_data)
                
                if converted_audio:
                    base64_audio = base64.b64encode(converted_audio).decode("utf-8")
                    data_object = {"is_text": False, "audio": base64_audio}
                    
                    await self.dispatcher.broadcast(
                        self.guid,
                        Message(
                            MessageHeader(MessageType.CALL_WEBSOCKET_PUT),
                            data=data_object,
                        ),
                    )
                    print(f"✅ Audio sent: '{text[:30]}...'")
                        
        except Exception as e:
            print(f"ElevenLabs TTS Exception: {e}")

    async def queue_for_audio_conversion(self, text: str):
        """Add text to audio conversion queue"""
        if text.strip():
            await self.audio_queue.put(text.strip())
            print(f"📤 Queued for audio: '{text.strip()}'")

    def is_sentence_end(self, text: str) -> bool:
        """Check if text ends with sentence-ending punctuation"""
        return bool(re.search(r'[.!?]\s*$', text.strip()))

    def is_pause_point(self, text: str) -> bool:
        """Check if text ends with a natural pause point"""
        return bool(re.search(r'[.!?,;:]\s*$', text.strip()))
    
    def is_too_short(self, text: str) -> bool:
        """Check if text is too short to send alone"""
        return len(text.strip().split()) < 3  # Less than 3 words

    async def flush_buffer(self, reason: str = ""):
        """Send the current buffer to TTS queue and clear it"""
        if self.is_processing:
            return
            
        if not self.word_buffer.strip():
            return
        
        # Don't send very short fragments alone
        if self.is_too_short(self.word_buffer) and reason != "forced":
            print(f"⏭️ Skipping short fragment: '{self.word_buffer.strip()}'")
            return
            
        self.is_processing = True
        
        try:
            buffer_content = self.word_buffer.strip()
            print(f"🎵 Flushing buffer ({reason}): '{buffer_content}'")
            
            # Clear buffer BEFORE queuing
            self.word_buffer = ""
            
            # Cancel any pending timer
            if self.buffer_timer:
                self.buffer_timer.cancel()
                self.buffer_timer = None
            
            # Queue for audio conversion (non-blocking)
            await self.queue_for_audio_conversion(buffer_content)
            
        finally:
            self.is_processing = False

    async def schedule_buffer_flush(self):
        """Schedule a buffer flush after a delay"""
        if self.buffer_timer:
            self.buffer_timer.cancel()
        
        async def delayed_flush():
            await asyncio.sleep(self.max_buffer_time)
            if not self.is_processing and self.word_buffer.strip():
                print(f"⏰ Timer flush")
                await self.flush_buffer("timer")
        
        self.buffer_timer = asyncio.create_task(delayed_flush())

    async def add_word_to_buffer(self, word: str):
        """Add word to buffer and decide when to send"""
        if self.is_processing:
            return
            
        self.word_buffer += word
        word_count = len(self.word_buffer.split())
        
        # Smarter logic to prevent fragmentation
        should_send = False
        reason = ""
        
        # 1. Sentence end - but check if it's not just punctuation
        if self.is_sentence_end(self.word_buffer):
            # Don't send if it's just punctuation (like standalone "?")
            if not self.is_too_short(self.word_buffer):
                should_send = True
                reason = "sentence_end"
            else:
                # If it's just punctuation, wait for more or let timer handle it
                await self.schedule_buffer_flush()
                return
        
        # 2. Pause point with enough words
        elif self.is_pause_point(self.word_buffer) and word_count >= 6:
            should_send = True
            reason = "pause_point"
        
        # 3. Buffer getting long
        elif word_count >= self.min_buffer_size:
            should_send = True
            reason = "buffer_size"
        
        if should_send:
            await self.flush_buffer(reason)
        else:
            # Schedule timer flush
            asyncio.create_task(self.schedule_buffer_flush())

    async def convert_audio_format(self, mp3_data: bytes) -> bytes:
        """Convert MP3 to 16kHz Linear16 PCM format expected by frontend"""
        try:
            loop = asyncio.get_event_loop()
            
            def _convert():
                audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
                audio = audio.set_frame_rate(16000)
                audio = audio.set_channels(1)
                audio = audio.set_sample_width(2)
                return audio.raw_data
            
            converted_audio = await loop.run_in_executor(None, _convert)
            return converted_audio
            
        except Exception as e:
            print(f"Audio conversion error: {e}")
            return None

    async def handle_llm_generated_text(self):
        # Start audio queue processor
        await self.start_audio_queue_processor()
        
        async with await self.dispatcher.subscribe(self.guid, MessageType.LLM_GENERATED_TEXT) as llm_generated_text:
            async for event in llm_generated_text:
                words = event.message.data.get("words")
                is_audio_required = event.message.data.get("is_audio_required")
                
                if is_audio_required and words:
                    await self.add_word_to_buffer(words)
                    
                    if self.send_buffer_event:
                        await self.dispatcher.broadcast(
                            self.guid,
                            Message(
                                MessageHeader(MessageType.CLEAR_EXISTING_BUFFER),
                                data={},
                            )
                        )
                        self.send_buffer_event = False

    async def handle_tts_flush(self):
        async with await self.dispatcher.subscribe(self.guid, MessageType.TTS_FLUSH) as flush_event:
            async for event in flush_event:
                print("🔄 TTS Flush event received")
                # Force flush any remaining buffer
                if self.word_buffer.strip():
                    await self.flush_buffer("forced")
                self.send_buffer_event = True

    async def run_async(self):
        await asyncio.gather(
            self.handle_llm_generated_text(),
            self.handle_tts_flush()
        )