import tkinter as tk
import socket
import threading
import json
import os

class BluetoothApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HC-05 Pro Controller")
        self.root.geometry("400x800")
        
        # Exact Kivy Theme Colors
        self.bg_main = "#0a192f"       
        self.bg_panel = "#112240"      
        self.bg_btn_normal = "#1e3a5f" 
        self.text_light = "#ccd6f6"    
        self.text_white = "#ffffff"    
        self.accent_teal = "#64ffda"   
        self.text_dark = "#0a192f"     
        self.color_success = "#00c853" 
        self.color_danger = "#d32f2f"  
        
        self.root.configure(bg=self.bg_main)

        self.bt_socket = None
        self.is_connected = False
        self.waiting_ack = False
        self.pending_data = ""
        
        # Variables (Default values)
        self.hc05_mac = tk.StringVar(value="98:D3:31:F4:XX:XX")
        self.on_delay = tk.StringVar(value="1000")
        self.off_delay = tk.StringVar(value="1000")
        self.s1_on_msg = tk.StringVar(value="S1_ON")
        self.s1_off_msg = tk.StringVar(value="S1_OFF")
        self.s2_on_msg = tk.StringVar(value="S2_ON")
        self.s2_off_msg = tk.StringVar(value="S2_OFF")

        # Load Saved Settings
        self.load_settings()

        self.setup_ui()
        threading.Thread(target=self.connect_bluetooth, daemon=True).start()

    # ==========================================
    # FILE SAVE & LOAD LOGIC
    # ==========================================
    def load_settings(self):
        if os.path.exists("bt_settings.json"):
            try:
                with open("bt_settings.json", "r") as f:
                    data = json.load(f)
                    if "mac" in data: self.hc05_mac.set(data["mac"])
                    if "on_delay" in data: self.on_delay.set(data["on_delay"])
                    if "off_delay" in data: self.off_delay.set(data["off_delay"])
                    if "s1_on" in data: self.s1_on_msg.set(data["s1_on"])
                    if "s1_off" in data: self.s1_off_msg.set(data["s1_off"])
                    if "s2_on" in data: self.s2_on_msg.set(data["s2_on"])
                    if "s2_off" in data: self.s2_off_msg.set(data["s2_off"])
            except Exception as e:
                print("Error loading settings:", e)

    def save_settings_to_file(self):
        data = {
            "mac": self.hc05_mac.get().strip(),
            "on_delay": self.on_delay.get(),
            "off_delay": self.off_delay.get(),
            "s1_on": self.s1_on_msg.get(),
            "s1_off": self.s1_off_msg.get(),
            "s2_on": self.s2_on_msg.get(),
            "s2_off": self.s2_off_msg.get()
        }
        try:
            with open("bt_settings.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            self.log(f"Save Error: {e}")

    def setup_ui(self):
        self.status_lbl = tk.Label(self.root, text="Disconnected", bg=self.color_danger, fg=self.text_white, font=("Arial", 14, "bold"), pady=8)
        self.status_lbl.pack(fill=tk.X)

        main_area = tk.Frame(self.root, bg=self.bg_main)
        main_area.pack(fill=tk.BOTH, expand=True)

        # TOP 50% SCREEN (Serial Monitor)
        top_half = tk.Frame(main_area, bg=self.bg_main)
        top_half.place(relx=0, rely=0, relwidth=1, relheight=0.5)

        self.monitor = tk.Text(top_half, bg="#000000", fg=self.accent_teal, font=("Courier", 6), relief=tk.FLAT, insertbackground=self.accent_teal)
        self.monitor.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.9) 
        self.log("UI Theme Applied Successfully...")
        self.log(f"Loaded MAC: {self.hc05_mac.get()}")

        # BOTTOM 50% SCREEN
        bottom_half = tk.Frame(main_area, bg=self.bg_main)
        bottom_half.place(relx=0, rely=0.5, relwidth=1, relheight=0.5)

        inner_frame = tk.Frame(bottom_half, bg=self.bg_main)
        inner_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        s1_frame = tk.Frame(inner_frame, bg=self.bg_main)
        s1_frame.pack(pady=15) 
        tk.Label(s1_frame, text="Slider 1", bg=self.bg_main, fg=self.text_light, font=("Arial", 18, "bold"), width=8, anchor="w").pack(side=tk.LEFT)
        self.create_large_slider(s1_frame, self.s1_toggle)

        s2_frame = tk.Frame(inner_frame, bg=self.bg_main)
        s2_frame.pack(pady=15)
        tk.Label(s2_frame, text="Slider 2", bg=self.bg_main, fg=self.text_light, font=("Arial", 18, "bold"), width=8, anchor="w").pack(side=tk.LEFT)
        self.create_large_slider(s2_frame, self.s2_toggle)

        # AHIYA FIX KARYU CHE: width kadi nakhi ane padx=40 karyu jethi exact center aave
        tk.Button(inner_frame, text="Settings", command=self.open_settings, bg=self.accent_teal, fg=self.text_dark, activebackground=self.bg_btn_normal, activeforeground=self.accent_teal, font=("Arial", 16, "bold"), relief=tk.FLAT, padx=40, pady=10).pack(pady=30)

    def create_large_slider(self, parent, command):
        canvas = tk.Canvas(parent, width=160, height=80, bg=self.bg_main, highlightthickness=0)
        canvas.pack(side=tk.LEFT, padx=10)
        
        bg_oval = canvas.create_oval(5, 5, 155, 75, fill=self.bg_btn_normal, outline=self.bg_btn_normal)
        circle = canvas.create_oval(12, 12, 68, 68, fill=self.text_light, outline=self.text_light)
        is_on = [False] 

        def toggle_click(event):
            is_on[0] = not is_on[0]
            if is_on[0]:
                canvas.itemconfig(bg_oval, fill=self.accent_teal, outline=self.accent_teal)
                canvas.itemconfig(circle, fill=self.text_dark, outline=self.text_dark)
                canvas.coords(circle, 92, 12, 148, 68) 
            else:
                canvas.itemconfig(bg_oval, fill=self.bg_btn_normal, outline=self.bg_btn_normal)
                canvas.itemconfig(circle, fill=self.text_light, outline=self.text_light)
                canvas.coords(circle, 12, 12, 68, 68) 
            command(is_on[0])

        canvas.bind("<Button-1>", toggle_click)

    def log(self, msg):
        self.monitor.insert(tk.END, msg + "\n")
        self.monitor.see(tk.END)

    def connect_bluetooth(self):
        mac = self.hc05_mac.get().strip()
        self.log(f"Searching HC-05 ({mac})...")
        try:
            self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.bt_socket.connect((mac, 1))
            self.is_connected = True
            
            threading.Thread(target=self.listen_for_ack, daemon=True).start()
            
            self.root.after(0, lambda: self.status_lbl.config(text="Connected via Bluetooth!", bg=self.color_success))
            self.root.after(0, lambda: self.log("HC-05 Connected Successfully!"))
        except Exception as e:
            self.is_connected = False
            self.root.after(0, lambda: self.status_lbl.config(text="Disconnected", bg=self.color_danger))
            self.root.after(0, lambda: self.log("Failed: HC-05 Not Found/Disabled."))

    def listen_for_ack(self):
        while self.is_connected and self.bt_socket:
            try:
                recv_data = self.bt_socket.recv(1024).decode("utf-8").strip()
                if recv_data:
                    self.root.after(0, lambda d=recv_data: self.log(f"RCV: {d}"))
                    if "OK" in recv_data.upper():
                        self.waiting_ack = False
            except:
                break

    def send_data(self, data, is_retry=False):
        if self.is_connected and self.bt_socket:
            try:
                self.bt_socket.send((data + "\n").encode("utf-8"))
                
                if is_retry:
                    self.log(f"RE-SENT: {data}")
                else:
                    self.log(f"SENT: {data}")
                
                self.waiting_ack = True
                self.pending_data = data
                self.root.after(3000, lambda: self.check_ack(data, is_retry))
                
            except:
                self.log("Send Error! Connection lost.")
                self.status_lbl.config(text="Disconnected", bg=self.color_danger)
                self.is_connected = False
        else:
            self.log(f"Simulated SENT: {data}")

    def check_ack(self, data, is_retry):
        if self.is_connected and self.waiting_ack and self.pending_data == data:
            if not is_retry:
                self.log("No message! Retrying...")
                self.send_data(data, is_retry=True)
            else:
                self.log("Controller Not Responding")
                self.waiting_ack = False 

    def s1_toggle(self, state):
        msg = self.s1_on_msg.get() if state else self.s1_off_msg.get()
        self.send_data(msg)

    def s2_toggle(self, state):
        msg = self.s2_on_msg.get() if state else self.s2_off_msg.get()
        self.send_data(msg)

    # ==========================================
    # SETTINGS OVERLAY
    # ==========================================
    def open_settings(self):
        self.overlay = tk.Frame(self.root, bg=self.bg_main)
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.popup = tk.Frame(self.overlay, bg=self.bg_panel, highlightbackground=self.accent_teal, highlightthickness=1)
        self.popup.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.96)

        tk.Label(self.popup, text="Button Value Settings", bg=self.bg_panel, fg=self.accent_teal, font=("Arial", 16, "bold")).pack(pady=10)

        list_frame = tk.Frame(self.popup, bg=self.bg_panel)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        fields = [
            ("MAC Address", self.hc05_mac),
            ("ON Delay", self.on_delay), 
            ("OFF Delay", self.off_delay),
            ("Slider 1 ON", self.s1_on_msg), 
            ("Slider 1 OFF", self.s1_off_msg),
            ("Slider 2 ON", self.s2_on_msg), 
            ("Slider 2 OFF", self.s2_off_msg),
        ]

        for label_text, var in fields:
            row_frame = tk.Frame(list_frame, bg=self.bg_panel)
            row_frame.pack(fill=tk.X, pady=6)

            tk.Label(row_frame, text=label_text, bg=self.bg_panel, fg=self.text_light, font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=2)
            
            entry = tk.Entry(row_frame, textvariable=var, bg=self.bg_main, fg=self.accent_teal, insertbackground=self.accent_teal, font=("Arial", 12), justify="center", bd=0, highlightthickness=1, highlightbackground=self.accent_teal, highlightcolor=self.accent_teal, width=16)
            entry.pack(side=tk.RIGHT, padx=2, ipady=5)
            
            entry.bind("<Button-1>", lambda e, widget=entry: widget.focus_set())

        tk.Button(self.popup, text="Save & Close", command=self.save_and_close_settings, bg=self.color_success, fg=self.text_dark, font=("Arial", 14, "bold"), relief=tk.FLAT, padx=25, pady=8).pack(pady=15)

    def save_and_close_settings(self):
        self.save_settings_to_file()
        
        data = f"SET:{self.on_delay.get()},{self.off_delay.get()}"
        self.send_data(data)
        
        self.overlay.destroy() 
        self.show_toast("Saved Successfully")

    def show_toast(self, message):
        toast_lbl = tk.Label(self.root, text=message, bg=self.accent_teal, fg=self.text_dark, font=("Arial", 14, "bold"), padx=25, pady=12, relief=tk.FLAT)
        toast_lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.root.after(2000, toast_lbl.destroy)

if __name__ == "__main__":
    root = tk.Tk()
    app = BluetoothApp(root)
    root.mainloop()
