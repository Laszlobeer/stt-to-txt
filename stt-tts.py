import sys
import os
import threading
import tempfile
import time
import queue
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QFileDialog, QComboBox, 
                             QMessageBox, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
import pyaudio
import wave
import whisper
import pyttsx3

class MicrophoneScanner(QObject):
    """Class to scan for available microphones"""
    
    @staticmethod
    def scan_with_pyaudio():
        """Scan microphones using PyAudio"""
        microphones = []
        try:
            p = pyaudio.PyAudio()
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                # Check if device is an input device (microphone)
                if device_info.get('maxInputChannels') > 0:
                    microphones.append({
                        'index': device_info.get('index'),
                        'name': device_info.get('name'),
                        'channels': device_info.get('maxInputChannels'),
                        'sample_rate': device_info.get('defaultSampleRate')
                    })
            
            p.terminate()
        except Exception as e:
            print(f"Error scanning microphones with PyAudio: {e}")
        
        return microphones
    
    @staticmethod
    def get_default_microphone():
        """Get the default microphone using PyAudio"""
        try:
            p = pyaudio.PyAudio()
            default_input = p.get_default_input_device_info()
            p.terminate()
            return {
                'index': default_input.get('index'),
                'name': default_input.get('name')
            }
        except Exception as e:
            print(f"Error getting default microphone: {e}")
            return None

class RealTimeTranscriber(QObject):
    update_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, model_size="base", chunk_length=3):
        super().__init__()
        self.model_size = model_size
        self.chunk_length = chunk_length
        self.model = None
        self.is_recording = False
        self.audio = None
        self.stream = None
        self.device_index = None
        self.audio_queue = queue.Queue()
        self.processing_thread = None

    def load_model(self):
        """Load the Whisper model"""
        try:
            self.status_signal.emit("Loading Whisper model...")
            self.model = whisper.load_model(self.model_size)
            self.status_signal.emit("Model loaded. Ready to transcribe.")
            return True
        except Exception as e:
            self.status_signal.emit(f"Error loading model: {str(e)}")
            return False

    def start_recording(self, device_index=None):
        """Start recording audio"""
        self.is_recording = True
        self.device_index = device_index
        
        try:
            self.audio = pyaudio.PyAudio()
            
            # If no device index specified, use default
            if self.device_index is None:
                default_info = self.audio.get_default_input_device_info()
                self.device_index = default_info["index"]
            
            # Audio parameters
            sample_rate = 16000
            channels = 1
            chunk_size = 1024
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=chunk_size
            )
            
            self.status_signal.emit("Recording... Speak now!")
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self.process_audio)
            self.processing_thread.start()
            
            # Record audio
            while self.is_recording:
                data = self.stream.read(chunk_size)
                self.audio_queue.put(data)
                
        except Exception as e:
            self.status_signal.emit(f"Recording error: {str(e)}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()

    def process_audio(self):
        """Process audio chunks for transcription"""
        sample_rate = 16000
        channels = 1
        chunk_size = 1024
        frames_per_chunk = int(sample_rate * self.chunk_length / chunk_size)
        
        while self.is_recording or not self.audio_queue.empty():
            try:
                # Collect enough frames for a chunk
                frames = []
                for _ in range(frames_per_chunk):
                    if self.is_recording or not self.audio_queue.empty():
                        frames.append(self.audio_queue.get(timeout=1))
                    else:
                        break
                
                if not frames:
                    continue
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    wf = wave.open(f.name, 'wb')
                    wf.setnchannels(channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    
                    # Transcribe
                    try:
                        result = self.model.transcribe(f.name)
                        text = result["text"].strip()
                        if text:
                            self.result_signal.emit(text)
                    except Exception as e:
                        self.status_signal.emit(f"Transcription error: {str(e)}")
                    
                    # Clean up
                    try:
                        os.unlink(f.name)
                    except:
                        pass
                        
            except queue.Empty:
                continue
            except Exception as e:
                self.status_signal.emit(f"Processing error: {str(e)}")
                time.sleep(0.1)

    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)

class TextToSpeechThread(QObject):
    update_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)

    def speak_text(self, text):
        try:
            self.update_signal.emit("Speaking...")
            self.engine.say(text)
            self.engine.runAndWait()
            self.update_signal.emit("Finished speaking.")
        except Exception as e:
            self.update_signal.emit(f"TTS error: {str(e)}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.transcriber = None
        self.recording_thread = None
        self.output_file = "transcription.txt"
        self.available_microphones = []
        self.is_recording = False
        self.initUI()
        self.scan_microphones()

    def initUI(self):
        self.setWindowTitle("Real-Time Whisper STT to TTS with GUI")
        self.setGeometry(100, 100, 700, 600)
        layout = QVBoxLayout()

        # Microphone selection section
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Select Microphone:"))
        
        self.mic_combo = QComboBox()
        self.mic_combo.currentIndexChanged.connect(self.mic_selection_changed)
        mic_layout.addWidget(self.mic_combo)
        
        self.refresh_mic_btn = QPushButton("Refresh")
        self.refresh_mic_btn.clicked.connect(self.scan_microphones)
        mic_layout.addWidget(self.refresh_mic_btn)
        
        layout.addLayout(mic_layout)

        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        # Model selection
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_dropdown.setCurrentText("base")
        layout.addWidget(QLabel("Select Whisper Model:"))
        layout.addWidget(self.model_dropdown)

        # Chunk length selection
        chunk_layout = QHBoxLayout()
        chunk_layout.addWidget(QLabel("Chunk Length (seconds):"))
        self.chunk_dropdown = QComboBox()
        self.chunk_dropdown.addItems(["1", "2", "3", "5", "10"])
        self.chunk_dropdown.setCurrentText("3")
        chunk_layout.addWidget(self.chunk_dropdown)
        layout.addLayout(chunk_layout)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Transcribed text will appear here in real-time...")
        layout.addWidget(self.text_edit)

        self.record_btn = QPushButton("Start Real-Time Transcription")
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn)

        self.play_btn = QPushButton("Play Text (TTS)")
        self.play_btn.clicked.connect(self.start_tts)
        layout.addWidget(self.play_btn)

        self.save_btn = QPushButton("Save to File")
        self.save_btn.clicked.connect(self.save_text)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def scan_microphones(self):
        """Scan for available microphones"""
        self.status_label.setText("Status: Scanning for microphones...")
        
        # Clear existing items
        self.mic_combo.clear()
        
        # Get available microphones
        self.available_microphones = MicrophoneScanner.scan_with_pyaudio()
        
        if not self.available_microphones:
            self.mic_combo.addItem("No microphones found")
            self.status_label.setText("Status: No microphones found!")
            return
        
        # Add microphones to combo box
        for mic in self.available_microphones:
            self.mic_combo.addItem(f"{mic['name']} (Ch: {mic['channels']}, Rate: {mic['sample_rate']})")
        
        # Try to select the default microphone
        default_mic = MicrophoneScanner.get_default_microphone()
        if default_mic:
            for i, mic in enumerate(self.available_microphones):
                if mic['index'] == default_mic['index']:
                    self.mic_combo.setCurrentIndex(i)
                    break
        
        self.status_label.setText(f"Status: Found {len(self.available_microphones)} microphone(s)")

    def mic_selection_changed(self, index):
        """Handle microphone selection change"""
        if index >= 0 and index < len(self.available_microphones):
            selected_mic = self.available_microphones[index]
            self.status_label.setText(f"Status: Selected {selected_mic['name']}")

    def toggle_recording(self):
        if self.is_recording:
            # Stop recording
            self.record_btn.setText("Start Real-Time Transcription")
            if self.transcriber:
                self.transcriber.stop_recording()
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
            self.is_recording = False
            self.status_label.setText("Status: Transcription stopped")
        else:
            # Start recording
            self.record_btn.setText("Stop Real-Time Transcription")
            self.is_recording = True
            
            # Get selected microphone index
            mic_index = None
            if self.mic_combo.currentIndex() >= 0 and self.mic_combo.currentIndex() < len(self.available_microphones):
                mic_index = self.available_microphones[self.mic_combo.currentIndex()]['index']
            
            # Get model size and chunk length
            model_size = self.model_dropdown.currentText()
            chunk_length = int(self.chunk_dropdown.currentText())
            
            # Initialize the transcriber
            self.transcriber = RealTimeTranscriber(model_size, chunk_length)
            
            # Load model in main thread to avoid issues
            if not self.transcriber.load_model():
                self.is_recording = False
                self.record_btn.setText("Start Real-Time Transcription")
                return
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(
                target=self.transcriber.start_recording, 
                args=(mic_index,)
            )
            self.transcriber.result_signal.connect(self.update_text)
            self.transcriber.status_signal.connect(self.update_status)
            self.recording_thread.start()

    def start_tts(self):
        text = self.text_edit.toPlainText()
        if text.strip():
            self.tts_worker = TextToSpeechThread()
            self.tts_thread = threading.Thread(
                target=self.tts_worker.speak_text, 
                args=(text,)
            )
            self.tts_worker.update_signal.connect(self.update_status)
            self.tts_thread.start()
        else:
            self.update_status("No text to speak.")

    def save_text(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Text File", "", "Text Files (*.txt)"
        )
        if file_path:
            self.output_file = file_path
            try:
                with open(self.output_file, "w", encoding="utf-8") as file:
                    file.write(self.text_edit.toPlainText())
                self.update_status(f"Text saved to {self.output_file}")
            except Exception as e:
                self.update_status(f"Error saving file: {str(e)}")

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def update_text(self, text):
        # Append new text to the text edit
        current_text = self.text_edit.toPlainText()
        if current_text:
            new_text = current_text + " " + text
        else:
            new_text = text
        self.text_edit.setText(new_text)
        self.save_text_to_file(new_text)

    def save_text_to_file(self, text):
        try:
            with open(self.output_file, "w", encoding="utf-8") as file:
                file.write(text)
        except Exception as e:
            self.update_status(f"Error saving file: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())