# Elbow Wrist Sync (影像與機械手臂同步監控系統)

*[English Version Below](#english-version)*

這是一個基於電腦視覺 (MediaPipe) 與物理模擬 (PyBullet) 的手部關節追蹤與機械手臂同步專案。透過網路攝影機即時捕捉人體的手肘、腕部角度以及手指張合度，並將其同步映射到 3D 模擬環境中的機器手臂，同時支援序列埠 (Serial) 輸出控制實體手臂，與記錄動作數據做為分析用途。

## 專案功能 (Features)
- **即時姿勢偵測 (Real-time Pose Detection)**：使用 MediaPipe 偵測肩、肘、腕關節與手指的空間座標，並計算出精準的夾角。
- **3D 模擬器同步 (PyBullet Simulation)**：在虛擬環境中即時反映真實世界的手臂姿態，方便於無實體硬體的情況下進行測試與預覽。
- **雜訊濾波 (Kalman & Median Filter)**：內建卡爾曼濾波結合中值濾波器，讓擷取的角度變化更平滑且穩定。
- **序列埠通訊 (Serial Communication)**：可以將轉換後的角度數據以高頻率 (如 20Hz) 發送給微控制器，用於實體手臂同步控制。
- **數據記錄與匯出 (Data Recording)**：內建校正與錄製功能，可將手肘/手腕角度與張合狀態匯出為 CSV 檔。

## 目錄結構 (Project Structure)
```text
elbow_wrist+sync/
├── data/                 # 系統自動建立，用於儲存錄製的 CSV 校正與數據檔
├── logs/                 # 存放錯誤日誌或系統運行記錄
├── project/              # 專案原始碼與資源主目錄
│   ├── assets/           # 模型檔資源 (如 simple_arm.urdf)
│   ├── utils/            # 功能模組
│   │   ├── detector.py   # MediaPipe 視覺偵測與角度計算邏輯
│   │   ├── filters.py    # Kalman 與中值濾波演算法
│   │   ├── recorder.py   # 負責將陣列資料錄製並寫入 CSV
│   │   └── sim_env.py    # PyBullet 3D 模擬環境建構與更新邏輯
│   └── main.py           # GUI 介面程式與系統整合主進入點
└── README.md             # 專案說明文件
```

## 系統需求 (Requirements)
本專案使用 Python 開發，建議使用 Python 3.8+。
請確保已經安裝以下相關套件：
- `opencv-python` (cv2)
- `mediapipe`
- `cvzone`
- `pybullet`
- `pyserial`
- `Pillow`
- `numpy`

## 使用方式 (How to Use)
1. 在終端機 / 命令提示字元進入 `project` 資料夾：
   ```bash
   cd project
   ```
2. 執行主程式：
   ```bash
   python main.py
   ```
3. 在 GUI 介面中：
   - 選擇要校正/觀察的模式 (Wrist 腕部 / Elbow 手肘 / Aperture 張合)。
   - 按下 `Record` 按鈕會開始錄製，預設為 10 秒倒數。
   - 畫面下方會顯示指示文字與紅色目標線，請跟隨目標線移動手臂。
   - 錄製結束後，數據會自動存成 CSV 檔，存放於專案根目錄的 `data/` 資料夾下。

## 硬體連接 (Hardware Connection)
若有連接實體手臂或微控制器：
- 請至 `project/main.py` 修改全域變數 `CONFIG` 區塊中的 `SERIAL_PORT` 為正確的 COM Port (例如 `COM3` 或是 Linux 下的 `/dev/ttyUSB0`)。
- 預設通訊傳輸格式為 `W:{腕部角度},E:{手肘角度},A:{張合度}\n`。

---

# English Version

# Elbow Wrist Sync

This is a hand joint tracking and robotic arm synchronization project based on computer vision (MediaPipe) and physical simulation (PyBullet). It captures real-time elbow angles, wrist angles, and finger aperture using a webcam, and maps them synchronously to a robotic arm in a 3D simulation environment. It also supports Serial communication for controlling physical robotic arms and records motion data for analysis.

## Features
- **Real-time Pose Detection**: Uses MediaPipe to detect spatial coordinates of the shoulder, elbow, wrist joints, and fingers, calculating precise angles.
- **3D Simulation Synchronization (PyBullet)**: Reflects real-world arm poses in a virtual environment in real-time, facilitating testing and previewing without physical hardware.
- **Noise Filtering (Kalman & Median Filter)**: Built-in Kalman filter combined with a median filter to make the extracted angle changes smoother and more stable.
- **Serial Communication**: Transmits the converted angle data at a high frequency (e.g., 20Hz) to a microcontroller for synchronized control of a physical arm.
- **Data Recording**: Built-in calibration and recording functionality that exports elbow/wrist angles and aperture status to a CSV file.

## Project Structure
```text
elbow_wrist+sync/
├── data/                 # Auto-generated directory for storing recorded CSV calibration data
├── logs/                 # Directory for storing error logs and system execution records
├── project/              # Main directory for source code and resources
│   ├── assets/           # 3D model resources (e.g., simple_arm.urdf)
│   ├── utils/            # Functional modules
│   │   ├── detector.py   # MediaPipe vision detection and angle calculation logic
│   │   ├── filters.py    # Kalman and median filtering algorithms
│   │   ├── recorder.py   # Logic for recording data arrays and writing to CSV
│   │   └── sim_env.py    # PyBullet 3D simulation environment setup and update logic
│   └── main.py           # GUI application and main system integration entry point
└── README.md             # Project documentation
```

## Requirements
This project is developed using Python (Python 3.8+ recommended).
Ensure the following packages are installed:
- `opencv-python` (cv2)
- `mediapipe`
- `cvzone`
- `pybullet`
- `pyserial`
- `Pillow`
- `numpy`

## How to Use
1. Open a terminal/command prompt and navigate to the `project` directory:
   ```bash
   cd project
   ```
2. Run the main application:
   ```bash
   python main.py
   ```
3. In the GUI:
   - Select the mode you want to calibrate or observe (Wrist / Elbow / Aperture).
   - Click the `Record` button to start recording (default is a 10-second countdown).
   - A red target line and instructions will appear at the bottom of the screen. Please follow the target line to move your arm.
   - After recording is complete, the data will automatically be saved as a CSV file in the `data/` folder located in the project root.

## Hardware Connection
If connecting to a physical robotic arm or microcontroller:
- Go to `project/main.py` and modify the `SERIAL_PORT` under the `CONFIG` section to the correct COM port (e.g., `COM3` on Windows or `/dev/ttyUSB0` on Linux).
- The default communication format is `W:{wrist_angle},E:{elbow_angle},A:{aperture_status}\n`.
