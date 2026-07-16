import tkinter as tk
from tkinter import ttk
import cv2
import time
from PIL import Image, ImageTk
from utils.detector import PoseDetector
from utils.recorder import DataRecorder
from utils.sim_env import PyBulletSim
from datetime import datetime
import serial

# ==== 全域配置 ====
CONFIG = {
    "SERIAL_PORT": "COM3",
    "BAUDRATE": 115200,
    "APERTURE_THRESHOLD": 30,
    "SERIAL_INTERVAL_MS": 50  # 傳輸間隔 (毫秒)，例如 50ms = 20Hz
}

class Application:
    def __init__(self, window, window_title="影像監控系統"):
        self.window = window
        self.window.title(window_title)
        
        # 定義三種模式的參數範圍與顯示屬性
        self.MODE_CFG = {
            "Wrist": {"name": "Wrist", "start": 90, "end": 180, "c_min": 0, "c_max": 180},
            "Elbow": {"name": "Elbow", "start": 0, "end": 90, "c_min": 0, "c_max": 180},
            "Aperture": {"name": "Aperture", "start": 150, "end": 50, "c_min": 0, "c_max": 200}
        }
        self.CALIBRATION_DURATION = 10  # 10秒倒數
        
        # 初始化 MediaPipe 偵測器 (帶入門檻值)
        self.detector = PoseDetector(aperture_threshold=CONFIG["APERTURE_THRESHOLD"])
        
        # 初始化錄製器
        self.recorder = DataRecorder()
        
        # 初始化 Serial 通訊
        self.ser = None
        try:
            self.ser = serial.Serial(CONFIG["SERIAL_PORT"], CONFIG["BAUDRATE"], timeout=0.1)
            print(f"Serial connected to {CONFIG['SERIAL_PORT']}")
        except Exception as e:
            print(f"Serial connection failed: {e}. Running without hardware.")

        self.last_serial_time = 0  # 記錄上次傳輸時間

        # 初始化 PyBullet 3D 模擬環境
        try:
            self.sim = PyBulletSim()
            print("PyBullet Simulator started.")
        except Exception as e:
            print(f"Failed to start PyBullet: {e}")
            self.sim = None

        # 打開 Webcam (預設鏡頭 0)
        self.vid = cv2.VideoCapture(0)
        
        # 建立主要 Frame
        self.main_frame = ttk.Frame(self.window, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 建立引導文字
        self.instruction_var = tk.StringVar(value="請將手完全伸直 (約 180°) 後按下 Record")
        self.instruction_label = ttk.Label(self.main_frame, textvariable=self.instruction_var, font=("Helvetica", 16, "bold"))
        self.instruction_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # ==== 模式選擇區域 ====
        self.mode_frame = ttk.LabelFrame(self.main_frame, text="模式選擇", padding="10")
        self.mode_frame.grid(row=0, column=2, sticky=(tk.N, tk.W, tk.E), padx=10, pady=(0, 10))
        
        self.current_mode = tk.StringVar(value="Wrist")
        
        ttk.Radiobutton(self.mode_frame, text="[Wrist] 腕部", variable=self.current_mode, value="Wrist", command=self.on_mode_change).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(self.mode_frame, text="[Elbow] 手肘", variable=self.current_mode, value="Elbow", command=self.on_mode_change).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(self.mode_frame, text="[Aperture] 張合度", variable=self.current_mode, value="Aperture", command=self.on_mode_change).pack(anchor=tk.W, pady=2)

        # ==== Canvas 引導條 ====
        self.canvas_width = 400
        self.canvas_height = 50
        self.progress_canvas = tk.Canvas(self.main_frame, width=self.canvas_width, height=self.canvas_height, bg="white", highlightthickness=1)
        self.progress_canvas.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # 畫背景橫線
        self.progress_canvas.create_line(20, 25, 380, 25, fill="gray", width=2)
        
        # 畫文字標籤
        self.canvas_min_text = self.progress_canvas.create_text(20, 10, text="0°", anchor=tk.W, fill="gray")
        self.canvas_max_text = self.progress_canvas.create_text(380, 10, text="180°", anchor=tk.E, fill="gray")
        
        # 畫模式標題標籤
        self.canvas_title_text = self.progress_canvas.create_text(200, 10, text="Elbow Calibration", anchor=tk.CENTER, fill="black", font=("Helvetica", 10, "bold"))
        
        # 建立目標指標 (紅色線)
        self.target_line = self.progress_canvas.create_line(
            0, 0, 0, self.canvas_height, fill="red", width=3, state=tk.HIDDEN
        )
        
        # 建立即時指標 (藍色小球)
        self.indicator_radius = 8
        self.indicator = self.progress_canvas.create_oval(
            0, 0, 0, 0,
            fill="blue", outline="darkblue"
        )
        
        # 顯示影像的 Label
        self.video_label = ttk.Label(self.main_frame)
        self.video_label.grid(row=2, column=0, rowspan=5, padx=10, pady=10)
        
        # 顯示數據的 Frame
        self.info_frame = ttk.LabelFrame(self.main_frame, text="即時角度數據", padding="10")
        self.info_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.N, tk.W, tk.E), padx=10, pady=10)
        
        # 數據綁定變數
        self.wrist_var = tk.StringVar(value="[Wrist] 腕部角度: 0.0°")
        self.elbow_var = tk.StringVar(value="[Elbow] 手肘角度: 0.0°")
        self.aperture_status_var = tk.StringVar(value="Aperture 狀態: 0")
        self.aperture_raw_var = tk.StringVar(value="Aperture 原始值: 0")
        
        # 數據標籤
        ttk.Label(self.info_frame, textvariable=self.wrist_var, font=("Helvetica", 14), foreground="orange").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(self.info_frame, textvariable=self.elbow_var, font=("Helvetica", 14), foreground="blue").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Aperture 顯示區域 (狀態與原始值分開或併列)
        ap_frame = ttk.Frame(self.info_frame)
        ap_frame.grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(ap_frame, textvariable=self.aperture_status_var, font=("Helvetica", 14, "bold"), foreground="green").pack(side=tk.LEFT)
        ttk.Label(ap_frame, textvariable=self.aperture_raw_var, font=("Helvetica", 12), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        
        # 分隔線
        ttk.Separator(self.info_frame, orient='horizontal').grid(row=3, column=0, sticky="ew", pady=10)
        
        # 錄製狀態與控制
        self.record_status_var = tk.StringVar(value="Status: Idle")
        self.record_count_var = tk.StringVar(value="Frames: 0")
        
        self.record_status_label = ttk.Label(self.info_frame, textvariable=self.record_status_var, font=("Helvetica", 12, "bold"))
        self.record_status_label.grid(row=4, column=0, sticky=tk.W, pady=2)
        
        self.record_count_label = ttk.Label(self.info_frame, textvariable=self.record_count_var, font=("Helvetica", 12))
        self.record_count_label.grid(row=5, column=0, sticky=tk.W, pady=2)
        
        self.btn_record = ttk.Button(self.info_frame, text="Record", command=self.toggle_recording)
        self.btn_record.grid(row=6, column=0, sticky=tk.W, pady=10)
        
        # 離開按鈕
        self.btn_quit = ttk.Button(self.main_frame, text="結束程式", command=self.on_closing)
        self.btn_quit.grid(row=6, column=2, sticky=(tk.S, tk.E), padx=10, pady=10)
        
        # 視窗關閉事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 迴圈更新影像更新的延遲 (ms)
        self.delay = 15 
        
        # 初次更新模式UI
        self.on_mode_change()
        
        self.update_video()
        
    def on_mode_change(self):
        # 取得當前模式資訊
        mode_key = self.current_mode.get()
        cfg = self.MODE_CFG[mode_key]
        
        start_a = cfg["start"]
        
        # 更新指示文字
        self.instruction_var.set(f"請將手放置於初始角度 ({start_a}°) 後按下 Record")
        self.instruction_label.configure(foreground="black")
        
        # 停止當前的錄影若正在進行中，避免資料混亂
        if self.recorder.is_recording:
            self.stop_recording()
            
        # 更新 Canvas 上方的極值和標題標籤
        self.progress_canvas.itemconfig(self.canvas_min_text, text=f"{cfg['c_min']}°")
        self.progress_canvas.itemconfig(self.canvas_max_text, text=f"{cfg['c_max']}°")
        self.progress_canvas.itemconfig(self.canvas_title_text, text=f"{mode_key} Calibration")

    def toggle_recording(self):
        if not self.recorder.is_recording:
            # 停用模式切換
            for child in self.mode_frame.winfo_children():
                child.configure(state=tk.DISABLED)
                
            self.recorder.start()
            self.record_status_var.set(f"● RECORDING ({self.current_mode.get()})")
            self.record_status_label.configure(foreground="red")
            self.btn_record.configure(text="Stop")
            
            # 顯示目標線
            self.progress_canvas.itemconfig(self.target_line, state=tk.NORMAL)
            
            # 更新指示文字為錄影狀態
            self.instruction_var.set(f"請跟隨紅線移動手臂... 剩餘 {self.CALIBRATION_DURATION:.1f} 秒")
            self.instruction_label.configure(foreground="red")
        else:
            self.stop_recording()
            
    def stop_recording(self):
        if self.recorder.is_recording:
            # {模式名稱}_{日期_時間}.csv
            mode_name = self.current_mode.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{mode_name}_{timestamp}.csv"
            
            self.recorder.stop(filename)
            self.record_status_var.set("Status: Idle")
            self.record_status_label.configure(foreground="black")
            self.btn_record.configure(text="Record")
            
            # 啟用模式切換
            for child in self.mode_frame.winfo_children():
                child.configure(state=tk.NORMAL)
            
            # 隱藏目標線
            self.progress_canvas.itemconfig(self.target_line, state=tk.HIDDEN)
            
            # 更新指示文字為停止狀態
            self.instruction_var.set("錄影結束，檔案已儲存")
            self.instruction_label.configure(foreground="black")
            
    def angle_to_canvas_x(self, angle, c_min, c_max):
        # 將角度轉為畫布上的 X 座標 (將數值線性對稱到 0~400)
        # 例如 c_min=0, c_max=180，則 angle 0 -> 0 px, 180 -> 400 px
        #     c_min=-90, c_max=180，則 angle -90 -> 0 px, 180 -> 400 px
        ratio = (angle - c_min) / float(c_max - c_min)
        x = ratio * self.canvas_width
        return max(0, min(x, self.canvas_width))

    def update_video(self):
        ret, frame = self.vid.read()
        if ret:
            # 翻轉影像(鏡像)，較為直覺
            frame = cv2.flip(frame, 1)
            # 取得當下模式的參數
            mode_key = self.current_mode.get()
            cfg = self.MODE_CFG[mode_key]

            # 一次性取得所有偵測數值 [wrist, elbow, aperture]
            annotated_frame, angles = self.detector.process_frame(frame)
            
            # 根據當前模式決定用於校正/指標的 current_val
            mode_key = self.current_mode.get()
            cfg = self.MODE_CFG[mode_key]
            
            if mode_key == "Wrist":
                current_val = angles[0]
            elif mode_key == "Elbow":
                current_val = angles[1]
            elif mode_key == "Aperture":
                current_val = angles[2]
            else:
                current_val = angles[0]
            
            # ==== 錄製與校正邏輯 ====
            if self.recorder.is_recording:
                # 計算經過時間
                elapsed_time = time.time() - self.recorder.start_time
                
                if elapsed_time > self.CALIBRATION_DURATION:
                    self.stop_recording()
                    current_target = cfg["end"]  # 最終值
                else:
                    # 計算目前的目標值
                    start_a = cfg["start"]
                    end_a = cfg["end"]
                    current_target = start_a - (start_a - end_a) * (elapsed_time / self.CALIBRATION_DURATION)
                    
                    self.recorder.add_entry(angles, current_target)
                    self.record_count_var.set(f"Frames: {len(self.recorder.data)}")
                    
                    # 更新提示文字
                    remaining_time = max(0, self.CALIBRATION_DURATION - elapsed_time)
                    self.instruction_var.set(f"請跟隨紅線移動手臂... 剩餘 {remaining_time:.1f} 秒")
                    
                    # 更新 Canvas 中的紅色目標線
                    target_x = self.angle_to_canvas_x(current_target, cfg["c_min"], cfg["c_max"])
                    self.progress_canvas.coords(
                        self.target_line, target_x, 0, target_x, self.canvas_height
                    )
            
            # 更新 Tkinter 標籤文字
            self.wrist_var.set(f"[Wrist] 腕部角度: {angles[0]}°")
            self.elbow_var.set(f"[Elbow] 手肘角度: {angles[1]}°")
            self.aperture_status_var.set(f"Aperture 狀態: {angles[2]}")
            self.aperture_raw_var.set(f"原始值: {angles[3]}")
            
            # ==== PyBullet 模擬即時同步 ====
            if self.sim:
                # 不改 pybullet，在這邊將 detector 角度變化反向
                # elbow: 原本是 0~180。加上負號可以直接反向變化
                rev_elbow = -angles[1]
                # wrist: 原本以 90 為基準 (0~180)。180 - angles[0] 可將其反向
                rev_wrist = 180 - angles[0]
                
                self.sim.update(rev_elbow, rev_wrist, angles[2])
            
            # ==== Serial 即時傳送 (定頻) ====
            current_time_ms = int(time.time() * 1000)
            if self.ser and self.ser.is_open:
                if (current_time_ms - self.last_serial_time) >= CONFIG["SERIAL_INTERVAL_MS"]:
                    try:
                        # 傳輸格式: W:腕部, E:手肘, A:張合
                        data_str = f"W:{angles[0]},E:{angles[1]},A:{angles[2]}\n"
                        print(f"Sending Serial Data: {data_str.strip()}")
                        self.ser.write(data_str.encode('utf-8'))
                        self.last_serial_time = current_time_ms
                    except Exception as e:
                        print(f"Serial write error: {e}")
            
            # ===== 更新 Canvas 指標位置 (藍色) =====
            # 藍色圓球跟隨所選模式的「即時角度」
            x_pos = self.angle_to_canvas_x(current_val, cfg["c_min"], cfg["c_max"])
            self.progress_canvas.coords(
                self.indicator,
                x_pos - self.indicator_radius, 25 - self.indicator_radius,
                x_pos + self.indicator_radius, 25 + self.indicator_radius
            )
            
            # OpenCV BGR 轉 RGB 以供 PIL 使用
            cv2image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            
            # 轉為 Tkinter 圖片格式
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        # 使用 after 避免卡死 GUI
        self.window.after(self.delay, self.update_video)
        
    def on_closing(self):
        # 結束錄製(如果正在錄製)
        self.stop_recording()
            
        # 釋放資源並關閉視窗
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")

        if self.vid.isOpened():
            self.vid.release()
            
        if self.sim:
            self.sim.disconnect()
            
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()
