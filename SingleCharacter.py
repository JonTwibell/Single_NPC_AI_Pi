import os
import re
import wave
import random
import glob
import time
import math
import struct
import subprocess
import pyaudio
from dotenv import load_dotenv
from groq import Groq
from elevenlabs import ElevenLabs

# Load API Keys
load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "HH3kybY6uEJ2ebSa9Vy3"

# Initialize SDK Clients
groq_client = Groq(api_key=GROQ_KEY)
eleven_client = ElevenLabs(api_key=ELEVEN_KEY)

# Audio Recording Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
AUDIO_INPUT_FILE = "input_mic.wav"
AUDIO_OUTPUT_FILE = "response.mp3"

# Silence & Threshold Parameters
SILENCE_LIMIT = 2.0  # Seconds of silence to trigger submission
SILENCE_THRESHOLD = 500  # RMS Volume Threshold (Adjust based on mic sensitivity)

# Pre-generated audio directories
STATEMENT_DIR = "./statement"
QUESTION_DIR = "./question"

# Optional Knowledge Base File (Path to a .txt file, or None/empty string if not using)
KNOWLEDGE_BASE_FILE = "BavlornaKB.json"

# Ready chime path (Using ALSA system sound on Raspberry Pi OS, or custom file)
READY_CHIME_PATH = "/usr/share/sounds/alsa/Front_Center.wav"

SYSTEM_INSTRUCTION = (
    "You are the hag Bavlorna Blightstraw from the Dungeons and Dragons adventure module The Wild Beyond the witchlight. You are Haggard, croaking hag obsessed with procrastination and gross practical efficiency. Speaks in a raspy, phlegmy, slurred monotone. Use informal, condescending language. Refer to mortals as little flies, pests, wet things, or troublesome morsels. Express deep irritation whenever anyone asks you to do work or stand up."
    "You have information for the party but they must meet the requirements fo you to provide the information. You know the following: Location of Zybilna's cauldron, weaknesses/obsessions of her sisters (Skabatha and Endelyn), location of stolen items in her cottage.  To gain the information the party must: Resolve a tedious chore (e.g., retrieving bobbin from TEL-uh-mee Hill, retrieving stolen goods from Agdon), or offer a valuable secret/trade adhering to the Rule of Reciprocity as outlined in the module. You will not give away details on the location of the items before they deliver on the bargan. KEY LORE & INFORMATION YOU HOLD: 1. The Cauldron of Plenty: You know Zybilna's magical cauldron is kept frozen in Prismeer, and the sisters of the Hourglass Coven split her power. 2. Sisterly Rivalry: You despise your sisters, Skabatha Nightshade (Thither) and Endelyn Moongrave (Yon). You know Skabatha hates anything unfinished, and Endelyn is obsessed with tragic prophecies. 3. Stolen Lost Things: You hold stolen trinkets and memories taken from visitors to the Witchlight Carnival. 4. The Rule of Reciprocity: You are bound by the Feywild Rule of Reciprocity—if someone does a service for you or gives you a gift, you are obligated to repay them in kind. CONDITIONS TO RELEASE INFORMATION: - Refuse all requests if the players simply demand answers or offer nothing in return. Tell them to clear off or go feed the lornlings. - If they perform a chore for you (e.g., fetching your bobbin from TEL‑uh‑mee Hill, retrieving stolen goods from Agdon Longscarf, or clean out your stagnant pool), you will reluctantly answer ONE question per task completed. - If they offer a genuine trade, secret, or valuable trinket under the Rule of Reciprocity, you will grudgingly fulfill your end of the bargain. BEHAVIORAL INSTRUCTIONS: - Respond ONLY in character. Your response will be used for text-to-voice so include only what should be said aloud and nothing else."
)

def load_knowledge_base(file_path):
    """Loads knowledge base text file if path exists and is defined."""
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    print(f"[+] Successfully loaded Knowledge Base from: {file_path}")
                    return f"\n\nADDITIONAL KNOWLEDGE BASE CONTEXT:\n{content}"
        except Exception as e:
            print(f"[x] Failed to load Knowledge Base file: {e}")
    else:
        if file_path:
            print(f"[-] Knowledge Base file not found: {file_path}. Continuing without KB.")
    return ""

def play_audio_file(file_path):
    """Plays WAV audio via aplay or MP3 audio via mpg123/ffplay across Raspberry Pi OS."""
    if not os.path.exists(file_path):
        return

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".wav":
        subprocess.run(["aplay", "-q", file_path])
    elif ext == ".mp3":
        # Fallback sequence depending on installed audio utilities
        if subprocess.run(["which", "mpg123"], capture_output=True).returncode == 0:
            subprocess.run(["mpg123", "-q", file_path])
        elif subprocess.run(["which", "ffplay"], capture_output=True).returncode == 0:
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path])
        else:
            subprocess.run(["cvlc", "--play-and-exit", file_path])

def play_ready_sound():
    """Plays system audio chime when the script is ready to listen."""
    print("[+] System Ready!")
    play_audio_file(READY_CHIME_PATH)

def calculate_rms(chunk):
    """Calculates the Root Mean Square volume of an audio frame chunk."""
    count = len(chunk) / 2
    format_str = f"%dh" % count
    shorts = struct.unpack(format_str, chunk)
    sum_squares = sum(s ** 2 for s in shorts)
    return math.sqrt(sum_squares / count) if count > 0 else 0

def record_audio_vad(output_filename, silence_limit=SILENCE_LIMIT):
    """Continuously listens and collects audio once voice is detected, stopping after silence_limit seconds."""
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("\n[!] Listening continuously... (Unmute mic to speak)")
    frames = []
    has_started_speaking = False
    silence_start_time = None

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        rms = calculate_rms(data)

        if rms > SILENCE_THRESHOLD:
            if not has_started_speaking:
                print("[+] Voice detected! Recording...")
                has_started_speaking = True
            frames.append(data)
            silence_start_time = None
        elif has_started_speaking:
            frames.append(data)
            if silence_start_time is None:
                silence_start_time = time.time()
            elif time.time() - silence_start_time >= silence_limit:
                print(f"[+] {silence_limit}s silence detected. Processing segment...")
                break

    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(output_filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def play_preroll_audio(user_text):
    """Plays a random pre-recorded mp3 from question or statement folder."""
    is_question = user_text.strip().endswith("?")
    folder = QUESTION_DIR if is_question else STATEMENT_DIR
    files = glob.glob(os.path.join(folder, "*.mp3"))

    if files:
        selected_file = random.choice(files)
        print(f"[+] Playing pre-roll sound: {selected_file}")
        play_audio_file(selected_file)

def transcribe_audio(file_path):
    """Sends recorded WAV file to Groq Whisper."""
    with open(file_path, "rb") as file:
        transcription = groq_client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3-turbo",
            response_format="text"
        )
    return transcription

def generate_llm_response(conversation_history):
    """Sends transcription to Groq LLM with chat history retained."""
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=conversation_history,
        temperature=0.7,
        max_tokens=1024,
        extra_body={"reasoning_format": "hidden"}
    )
    content = response.choices[0].message.content
    return content if content else "What do you want, little fly?"

def speak_text(text, voice_id):
    """Converts text to cloned voice via ElevenLabs and plays audio via Raspberry Pi utilities."""
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128"
    )
    
    with open(AUDIO_OUTPUT_FILE, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)
                
    play_audio_file(AUDIO_OUTPUT_FILE)

def main():
    # Initialize folder structures if missing
    os.makedirs(STATEMENT_DIR, exist_ok=True)
    os.makedirs(QUESTION_DIR, exist_ok=True)

    # Combine core instructions with optional knowledge base at startup
    kb_context = load_knowledge_base(KNOWLEDGE_BASE_FILE)
    full_system_instruction = SYSTEM_INSTRUCTION + kb_context

    # Initialize conversation history with system instructions at launch
    conversation_history = [{"role": "system", "content": full_system_instruction}]

    print("[+] Conversation session initialized with system persona & knowledge base.")
    
    # Play chime indicating system readiness
    play_ready_sound()

    while True:
        try:
            record_audio_vad(AUDIO_INPUT_FILE, silence_limit=SILENCE_LIMIT)

            user_text = transcribe_audio(AUDIO_INPUT_FILE)
            clean_text = user_text.strip()

            if not clean_text:
                print("[-] No transcript detected. Retrying...")
                continue

            print(f"\nUser Said: \"{clean_text}\"")

            # 1. Play pre-recorded buffer file based on input sentence end-point
            play_preroll_audio(clean_text)

            # 2. Append turn to persistent history context
            conversation_history.append({"role": "user", "content": clean_text})

            # 3. Generate response using single maintained context
            llm_reply = generate_llm_response(conversation_history)
            print(f"AI Reply: \"{llm_reply.strip()}\"")

            # 4. Save response to history and synthesize audio output
            conversation_history.append({"role": "assistant", "content": llm_reply})
            speak_text(llm_reply, VOICE_ID)

        except KeyboardInterrupt:
            print("\n[+] Exiting conversation loop.")
            break
        except Exception as e:
            print(f"[x] Error encountered: {e}")

if __name__ == "__main__":
    main()