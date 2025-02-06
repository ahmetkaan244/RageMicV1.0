import pyaudio
import numpy as np
import tkinter as tk
from tkinter import ttk
import keyboard
import threading
import queue
class AudioProcessor:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.active = False
        self.input_device = None
        self.output_device = None
        self.stream = None
        self.gain = 1.0
        self.distortion = 1.0
        self.clipping = 1.0
        self.effects_enabled = False

        # Create audio buffer queue
        self.audio_queue = queue.Queue(maxsize=10)

    def get_device_list(self, device_type):
        devices = []
        seen_devices = set()
        host_api_count = self.p.get_host_api_count()
        host_api_names = {}
        for i in range(host_api_count):
            host_api_info = self.p.get_host_api_info_by_index(i)
            host_api_names[i] = host_api_info['name']
        for i in range(self.p.get_device_count()):
            dev_info = self.p.get_device_info_by_index(i)
            host_api = host_api_names.get(dev_info['hostApi'], 'Unknown API')
            if host_api != "MME":
                continue
            device_name = dev_info['name']
            device_key = (device_name, host_api)
            if device_key in seen_devices:
                continue
            seen_devices.add(device_key)
            if device_type == 'input' and dev_info['maxInputChannels'] > 0:
                devices.append(f"{i}: {device_name} ({host_api})")
            elif device_type == 'output' and dev_info['maxOutputChannels'] > 0:
                devices.append(f"{i}: {device_name} ({host_api})")
        return devices

    def process_audio(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.float32)

        if self.effects_enabled:
            # Apply gain 
            audio_data = audio_data * (self.gain ** 2)

            # Apply distortion 
            audio_data = np.tanh(audio_data * self.distortion * 10)

            # Stack another layer of distortion for more intensity
            audio_data = np.tanh(audio_data * 2)

            # Apply clipping 
            audio_data = np.clip(audio_data, -self.clipping, self.clipping)

        return (audio_data.tobytes(), pyaudio.paContinue)

    def start_stream(self, input_device_index, output_device_index):
        if self.stream is not None:
            self.stop_stream()

        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=44100,
            input=True,
            output=True,
            input_device_index=input_device_index,
            output_device_index=output_device_index,
            stream_callback=self.process_audio,
            frames_per_buffer=1024
        )
        self.stream.start_stream()

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def cleanup(self):
        self.stop_stream()
        self.p.terminate()

class AudioEffectGUI:
    def __init__(self):
        self.processor = AudioProcessor()
        self.root = tk.Tk()
        self.root.title("RAGE MODE - ahmetkaan244")
        self.root.geometry("500x600")
        style = ttk.Style()
        style.theme_use('clam')
        

        # Set the fixed toggle key
        self.toggle_key = "f6"

        self.profile_settings = {
            "Ses arttırma": {"gain": 1.0, "distortion": 1.0, "clipping": 1.0},
            "Kızarmış ses": {"gain": 5.0, "distortion": 20.0, "clipping": 0.5},
            "Cinnet modu": {"gain": 10.0, "distortion": 35.0, "clipping": 0.3}
        }
        self.setup_ui()
        self.setup_hotkey()

    def setup_ui(self):
        # Overall frame for padding
        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Device selection frame
        input_frame = ttk.LabelFrame(main_frame, text="Ses Aygıtları")
        input_frame.pack(padx=5, pady=5, fill="x")

        ttk.Label(input_frame, text="Mikrofonunuzu seçin:").pack(pady=2)
        self.input_device_var = tk.StringVar()
        self.input_device_combo = ttk.Combobox(input_frame, textvariable=self.input_device_var, state="readonly")
        self.input_device_combo['values'] = self.processor.get_device_list('input')
        self.input_device_combo.pack(padx=5, pady=5, fill="x")

        ttk.Label(input_frame, text="Çıkış (CABLE INPUT-VB-Cable):").pack(pady=2)
        self.output_device_var = tk.StringVar()
        self.output_device_combo = ttk.Combobox(input_frame, textvariable=self.output_device_var, state="readonly")
        self.output_device_combo['values'] = self.processor.get_device_list('output')
        self.output_device_combo.pack(padx=5, pady=5, fill="x")

        # Profile selection frame
        profile_frame = ttk.LabelFrame(main_frame, text="Profil Seçimi")
        profile_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(profile_frame, text="Ön ayarlar:").pack(pady=2)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly")
        self.profile_combo['values'] = list(self.profile_settings.keys())
        self.profile_combo.current(0)
        self.profile_combo.pack(padx=5, pady=5, fill="x")
        self.profile_combo.bind("<<ComboboxSelected>>", self.apply_profile)

        # Effects controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Ayarlar")
        controls_frame.pack(padx=5, pady=5, fill="x")

        # Gain control
        ttk.Label(controls_frame, text="Ses seviyesi:").pack(pady=2)
        self.gain_scale = ttk.Scale(controls_frame, from_=0, to=20, orient="horizontal", command=self.update_gain)
        self.gain_scale.set(self.profile_settings[self.profile_var.get()]["gain"])
        self.gain_scale.pack(fill="x", padx=5, pady=5)

        # Distortion control
        ttk.Label(controls_frame, text="Bozukluk seviyesi:").pack(pady=2)
        self.distortion_scale = ttk.Scale(controls_frame, from_=1, to=50, orient="horizontal", command=self.update_distortion)
        self.distortion_scale.set(self.profile_settings[self.profile_var.get()]["distortion"])
        self.distortion_scale.pack(fill="x", padx=5, pady=5)

        # Clipping control
        ttk.Label(controls_frame, text="Kırılma seviyesi:").pack(pady=2)
        self.clipping_scale = ttk.Scale(controls_frame, from_=0.01, to=1, orient="horizontal", command=self.update_clipping)
        self.clipping_scale.set(self.profile_settings[self.profile_var.get()]["clipping"])
        self.clipping_scale.pack(fill="x", padx=5, pady=5)

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(padx=5, pady=5, fill="x")

        # Toggle button for processing
        self.toggle_button = ttk.Button(buttons_frame, text="Buraya Basarak Çalıştır(" + self.toggle_key.upper() + ")", 
                                         command=lambda: self.toggle_processing(None))
        self.toggle_button.pack(pady=5, fill="x")

        # Extra Info button
        self.extra_info_button = ttk.Button(buttons_frame, text="Program çalışmıyor?", command=self.show_extra_info)
        self.extra_info_button.pack(pady=5, fill="x")

        # Status label
        self.status_label = ttk.Label(main_frame, text="Durum: RAGE MODE OFF", anchor="center")
        self.status_label.pack(pady=10, fill="x")

    def apply_profile(self, event=None):
        profile = self.profile_var.get()
        settings = self.profile_settings.get(profile, {})
        # Update sliders
        self.gain_scale.set(settings.get("gain", 1.0))
        self.distortion_scale.set(settings.get("distortion", 1.0))
        self.clipping_scale.set(settings.get("clipping", 1.0))
        # Update processor values immediately
        self.processor.gain = float(settings.get("gain", 1.0))
        self.processor.distortion = float(settings.get("distortion", 1.0))
        self.processor.clipping = float(settings.get("clipping", 1.0))

    def setup_hotkey(self):
        
        keyboard.on_press_key(self.toggle_key, self.toggle_processing)

    def show_extra_info(self):
        # Create a new window with a multiline text box.
        extra_win = tk.Toplevel(self.root)
        extra_win.title("Ekstra Bilgi")
        extra_win.geometry("400x300")
        # Use a Text widget
        text_box = tk.Text(extra_win, wrap="word", bg="#3c3f41", fg="white")
        text_box.pack(expand=True, fill="both", padx=5, pady=5)
        
        extra_text = (
            "Program çalışmıyor mu? \n"
            "Cable input kurulu ama gözükmüyor : 64-bit cable input kurmuş olman gerekiyor. kurduktan sonra restart at.\n"
            "\n"
            "Illegal combination hatası : Mikrofonun ve CABLE INPUT kısımlarının doğru seçilmiş olması gerekiyor.\n"
            "\n"
            "Invalid literal hatası : aga önce bi mikrofonunu seçeydin ya listeden, bu ne acele?\n"
            "\n"
            "Abi bu virüs mü? evet abi bu virüs, çok korkutucu bööö.\n"
            "Pythondan yapılan uygulamalar herhangi bir sertifika vermeden buildleyince antivirüsü tetikler.\n"
            "Ayrıca oyundayken çalışması için 'keyboard' modülü kullanıyor ve bu nedenden dolayı keylogger gibi gözüküyor.\n"
            
        )
        text_box.insert("1.0", extra_text)
        text_box.config(state="disabled")

    def toggle_processing(self, e):
        if not self.processor.stream:
            try:
                input_idx = int(self.input_device_var.get().split(':')[0])
                output_idx = int(self.output_device_var.get().split(':')[0])
                self.processor.start_stream(input_idx, output_idx)
                self.processor.effects_enabled = True
                self.status_label.config(text="Durum: RAGE MODE ON")
               
            except Exception as err:
                self.status_label.config(text=f"Error: {str(err)}")
        else:
            if self.processor.effects_enabled:
                self.processor.effects_enabled = False
                self.status_label.config(text="Durum: RAGE MODE OFF")
                self.toggle_button.config(text="KULAKLARI YOK ET! (" + self.toggle_key.upper() + ")")
            else:
                self.processor.effects_enabled = True
                self.status_label.config(text="Durum: RAGE MODE ON")
                self.toggle_button.config(text="NORMAL MODA GEÇ (" + self.toggle_key.upper() + ")")

    def update_gain(self, value):
        self.processor.gain = float(value)

    def update_distortion(self, value):
        self.processor.distortion = float(value)

    def update_clipping(self, value):
        self.processor.clipping = float(value)

    def run(self):
        self.root.mainloop()
        self.processor.cleanup()

if __name__ == "__main__":
    app = AudioEffectGUI()
    app.run()
