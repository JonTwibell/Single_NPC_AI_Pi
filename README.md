# Bavlorna — Voice-Driven AI Character for Raspberry Pi

A hands-free voice assistant that plays an AI-driven D&D character. It listens continuously through a microphone, transcribes speech with Groq Whisper, generates an in-character reply with a Groq LLM, and speaks it back using an ElevenLabs cloned voice.

Out of the box it's configured as **Bavlorna Blightstraw**, the hag from *The Wild Beyond the Witchlight*, but the persona is just a string in the script — swap it for any character you like.

## How It Works

1. **Voice activity detection** — the script streams mic audio and watches the RMS volume. Recording starts when you speak and stops after a configurable period of silence.
2. **Transcription** — the captured WAV is sent to Groq's `whisper-large-v3-turbo`.
3. **Pre-roll filler** — while the LLM thinks, a random pre-recorded MP3 plays from `question/` or `statement/`, depending on whether your sentence ended in a question mark. This hides the API latency. (You can use ElevenLabs to record a mummer or sound someone might make while thinking or a narrator saying something like: Bavlorna studies you for a moment.")
4. **Response generation** — the full conversation history (plus system persona and optional knowledge base) goes to a Groq chat model.
5. **Speech synthesis** — the reply is converted to audio by ElevenLabs and played back through ALSA.

Conversation history persists for the lifetime of the process, so the character remembers the session.

## Requirements

### Hardware

- Raspberry Pi (tested on Raspberry Pi OS)
- USB microphone or compatible audio input
- Speaker or audio output device

### Accounts

- A [Groq](https://console.groq.com/) API key (transcription + LLM)
- An [ElevenLabs](https://elevenlabs.io/) API key (text-to-speech)

## Installation

Clone the repo and run the setup script:

```bash
git clone https://github.com/JonTwibell/Single_NPC_AI_Pi
cd <your-repo-folder>
chmod +x setup.sh
./setup.sh
```

`setup.sh` will:

- Install system audio dependencies (`portaudio19-dev`, `libasound2-dev`, `alsa-utils`, `mpg123`, `ffmpeg`)
- Create a Python virtual environment in `venv/`
- Install `pyaudio`, `python-dotenv`, `groq`, and `elevenlabs`
- Create the `statement/` and `question/` pre-roll directories
- Generate a `.env` template if one doesn't exist

## Configuration

### API Keys

Edit `.env` and fill in your keys:

```bash
nano .env
```

```ini
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

### Voice

Set `VOICE_ID` near the top of `SingleCharacter.py` to the ElevenLabs voice you want to use.

### Tuning Parameters

These constants at the top of `SingleCharacter.py` control the listening behavior:

| Constant | Default | Purpose |
| --- | --- | --- |
| `SILENCE_THRESHOLD` | `500` | RMS volume above which audio counts as speech. Raise it in noisy rooms, lower it if your mic is quiet. |
| `SILENCE_LIMIT` | `2.0` | Seconds of silence before the script stops recording and submits. |
| `RATE` | `16000` | Mic sample rate in Hz. |
| `CHUNK` | `1024` | Frames per audio buffer. |

`SILENCE_THRESHOLD` is the one you'll most likely need to adjust — it depends entirely on your microphone's sensitivity.

### Persona

`SYSTEM_INSTRUCTION` in `SingleCharacter.py` defines the character's voice, knowledge, and behavioral rules. Replace it wholesale to build a different character.

### Knowledge Base (Optional)

Set `KNOWLEDGE_BASE_FILE` to the path of a text or JSON file (default: `BavlornaKB.json`) and its contents will be appended to the system instruction at startup. If the file is missing, the script logs a notice and continues without it.

### Pre-Roll Audio (Optional)

Drop short MP3 clips into these folders to cover API latency:

- `statement/` — played when the user's input does **not** end in `?`
- `question/` — played when it does

Think grumbles, sighs, or "hmm, let me think..." — anything in character. If the folders are empty, the step is skipped silently.

## Running Manually

```bash
source venv/bin/activate
python3 SingleCharacter.py
```

A chime plays once the system is ready to listen. Press `Ctrl+C` to exit.

---

# Running as a systemd Service

To have the script start automatically on boot and restart if it crashes, install it as a systemd service.

## 1. Create the Service File

Open a terminal on your Raspberry Pi and create a new systemd service file:

```bash
sudo nano /etc/systemd/system/bavlorna.service
```

Paste the following configuration into the editor:

```ini
[Unit]
Description=Bavlorna AI Character Script
After=network-online.target sound.target
Wants=network-online.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/your_project_folder
ExecStart=/home/pi/your_project_folder/venv/bin/python3 /home/pi/your_project_folder/SingleCharacter.py
Restart=on-failure
RestartSec=5s

# Audio environment configuration
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=multi-user.target
```

> **Note:** Update `/home/pi/your_project_folder` to match the exact absolute
> directory path where your project and `venv` folder are located
> (e.g. `/home/pi/bavlorna`). If your username is not `pi`, change `User=pi`
> to your actual username.

## 2. Enable and Start the Service

Reload the systemd daemon to register the new configuration, then enable the service to boot automatically and start it immediately:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bavlorna.service
sudo systemctl start bavlorna.service
```

## 3. Service Management Commands

**Check status:**

```bash
sudo systemctl status bavlorna.service
```

**View live print logs (stdout/stderr):**

```bash
sudo journalctl -u bavlorna.service -f
```

**Stop the service:**

```bash
sudo systemctl stop bavlorna.service
```

**Restart the service:**

```bash
sudo systemctl restart bavlorna.service
```

---

## Troubleshooting

**No audio input detected** — list capture devices with `arecord -l` and confirm your mic is present. Test with `arecord -d 5 test.wav && aplay test.wav`.

**Script never stops recording** — `SILENCE_THRESHOLD` is too low for your ambient noise level. Raise it.

**Script never starts recording** — `SILENCE_THRESHOLD` is too high, or your mic gain is too low. Adjust with `alsamixer`.

**No sound on playback** — verify the output device with `aplay -l` and set the default via `sudo raspi-config` or `~/.asoundrc`.

**Service runs but produces no audio** — confirm the `User=` in the unit file matches the user who owns the audio session, and that `XDG_RUNTIME_DIR` points at that user's ID (`id -u <username>`).

**`pyaudio` fails to install** — make sure `portaudio19-dev` is installed before pip runs; `setup.sh` handles this ordering.

## Files

| File | Purpose |
| --- | --- |
| `SingleCharacter.py` | Main application loop |
| `setup.sh` | One-shot environment and dependency installer |
| `.env` | API keys (not committed) |
| `statement/`, `question/` | Pre-roll MP3 clips |
| `input_mic.wav` | Scratch file for the current recording |
| `response.mp3` | Scratch file for the current TTS output |

## Notes For Git Edit

Keep `.env` out of version control. A `.gitignore` containing at least the following is recommended:

```gitignore
.env
venv/
input_mic.wav
response.mp3
```
