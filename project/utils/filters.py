import numpy as np
from collections import deque

class KalmanMedianFilter:
    def __init__(self, median_window=5, Q=0.01, R=0.1):
        """
        結合中值濾波器與卡爾曼濾波器的 1D 濾波器
        
        :param median_window: 中值濾波器的視窗大小 (建議為奇數，如 3, 5, 7)
        :param Q: 卡爾曼濾波的過程雜訊協方差 (越小越平滑，但也越遲鈍)
        :param R: 卡爾曼濾波的量測雜訊協方差 (越大越不信任即時數據)
        """
        # 中值濾波器參數
        self.window_size = median_window
        self.buffer = deque(maxlen=median_window)
        
        # 卡爾曼濾波器狀態
        self.Q = Q  # Process noise
        self.R = R  # Measurement noise
        self.x = None  # 目前估計值 (Posterior state estimate)
        self.P = 1.0   # 估計誤差協方差 (Posterior error covariance)

    def update(self, measurement):
        """輸入原始數值，回傳濾波後的結果"""
        
        # 1. 中值濾波 - 用於剔除突跳雜訊 (Outliers)
        self.buffer.append(measurement)
        if len(self.buffer) < self.window_size:
            # 緩衝區未滿時，先直接回傳或使用簡單中值
            median_val = np.median(list(self.buffer))
        else:
            median_val = np.median(list(self.buffer))
            
        # 2. 卡爾曼濾波 - 用於平滑數值漂移
        if self.x is None:
            self.x = median_val
            return float(self.x)
        
        # --- Prediction step ---
        # x_p = x (假設狀態不變)
        # P_p = P + Q
        p_prior = self.P + self.Q
        
        # --- Update step ---
        # K = P_p / (P_p + R)
        k_gain = p_prior / (p_prior + self.R)
        
        # x = x_p + K * (z - x_p)
        self.x = self.x + k_gain * (median_val - self.x)
        
        # P = (1 - K) * P_p
        self.P = (1 - k_gain) * p_prior
        
        return float(self.x)
