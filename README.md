# Real-Time Speech-to-Text to Speech (STT-TTS) Application

A Python application that provides real-time speech recognition using OpenAI's Whisper model and text-to-speech capabilities using pyttsx3. Built with PyQt5 for the graphical user interface.

## Features

- **Real-time Speech Recognition**: Convert spoken words to text using Whisper AI
- **Text-to-Speech**: Convert transcribed text back to speech
- **Microphone Selection**: Choose from available input devices
- **Adjustable Settings**: Select different Whisper models and audio chunk sizes
- **Save Transcripts**: Export transcribed text to files
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Requirements

- Python 3.7+
- PyAudio
- OpenAI Whisper
- PyQt5
- pyttsx3

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd stt-tts-app
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

Alternatively, install packages individually:
```bash
pip install PyAudio whisper PyQt5 pyttsx3
```

Note: On some systems, you might need to install additional dependencies for PyAudio:
- Windows: Use pip install
- macOS: `brew install portaudio`
- Linux: `sudo apt-get install python-pyaudio python3-pyaudio portaudio19-dev`

## Usage

1. Run the application:
```bash
python stt-tts.py
```

2. Select your microphone from the dropdown menu
3. Choose your preferred Whisper model size (tiny, base, small, medium, large)
4. Set the chunk length for audio processing
5. Click "Start Real-Time Transcription" to begin
6. Speak into your microphone - text will appear in real-time
7. Use "Play Text (TTS)" to hear the transcribed text spoken back
8. Save your transcript using "Save to File"

## Model Information

The application supports different Whisper model sizes:
- **tiny**: Fastest, lowest accuracy
- **base**: Good balance of speed and accuracy
- **small**: Better accuracy, slower
- **medium**: High accuracy, slower
- **large**: Highest accuracy, slowest

Larger models provide better transcription accuracy but require more system resources and processing time.

## File Structure

```
stt-tts-app/
├── stt-tts.py      # Main application file
├── requirements.txt # Python dependencies
└── README.md       # This file
```

## Troubleshooting

- If you encounter issues with microphone detection, try refreshing the microphone list
- Ensure your microphone has proper permissions on your operating system
- For better performance, use a smaller model if you have limited system resources
- If you experience audio quality issues, try adjusting the chunk length

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
