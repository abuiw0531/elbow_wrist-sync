import cv2
import math
import mediapipe as mp
from cvzone.PoseModule import PoseDetector as CvzoneDetector
from cvzone.HandTrackingModule import HandDetector
from .filters import KalmanMedianFilter

def clamp(n, minn, maxn):
    """輔助函式：限位鎖定"""
    return max(minn, min(n, maxn))

def calculate_angle(a, b, c):
    """計算由 a, b, c 三點形成的夾角，其中 b 為頂點"""
    ang = math.degrees(
        math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0])
    )
    return abs(ang)

class PoseDetector:
    def __init__(self, aperture_threshold=75):
        """初始化 cvzone 姿勢偵測器與 MediaPipe Hands"""
        self.detector = CvzoneDetector(staticMode=False, modelComplexity=1)
        self.hand_detector = HandDetector(detectionCon=0.7, maxHands=1)
        self.aperture_threshold = aperture_threshold
        
        # 初始化 MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.last_annotated_frame = None
        
        # 初始化濾波器 (調整 Q, R 來改變平滑度)
        self.wrist_filter = KalmanMedianFilter(median_window=5, Q=0.05, R=0.5)
        self.elbow_filter = KalmanMedianFilter(median_window=5, Q=0.05, R=0.5)

    def process_frame(self, frame):
        """一次性執行所有偵測，回傳繪製好的影像與數據 [wrist, elbow, aperture_binary, aperture_raw]"""
        # 1. 姿勢偵測 (手臂/手肘)
        annotated_frame = self.detector.findPose(frame, draw=True)
        lm_pose, _ = self.detector.findPosition(annotated_frame, draw=False)
        
        elbow_angle = 0
        pose_elbow = None
        if lm_pose:
            # 手肘角度 (肩-肘-腕)
            p1 = lm_pose[11][0:2] # 左肩
            p2 = lm_pose[13][0:2] # 左肘
            p3 = lm_pose[15][0:2] # 左腕
            angle, _ = self.detector.findAngle(p1, p2, p3, img=annotated_frame)
            # 反轉邏輯：原本 180 變 0，原本 0 變 180
            elbow_angle_raw = clamp(180 - int(angle), 0, 180)
            # 應用濾波
            elbow_angle = int(self.elbow_filter.update(elbow_angle_raw))
            pose_elbow = p2

        # 2. 手部偵測 (腕部角度 & Aperture)
        hands, annotated_frame = self.hand_detector.findHands(annotated_frame, draw=True, flipType=False)
        
        wrist_angle = 0
        aperture_raw = 0
        aperture_binary = 0
        
        if hands:
            hand1 = hands[0]
            # 計算 Aperture (拇指 4 與 食指 8)
            p_thumb = hand1['lmList'][4][:2]
            p_index = hand1['lmList'][8][:2]
            length, _, annotated_frame = self.hand_detector.findDistance(p_thumb, p_index, annotated_frame)
            aperture_raw = int(length)
            
            # Aperture 二元化邏輯
            aperture_binary = 1 if aperture_raw > self.aperture_threshold else 0
            
            # 計算手腕角度 (需搭配手肘位置)
            if pose_elbow:
                hand_wrist = hand1['lmList'][0][:2]
                hand_mid_base = hand1['lmList'][9][:2]
                wrist_angle_raw = calculate_angle(pose_elbow, hand_wrist, hand_mid_base)
                # Wrist 轉換邏輯：水平中心顯示 90，往上靠近 0，往下靠近 180
                wrist_angle_raw = clamp(270 - int(wrist_angle_raw), 0, 180)
                # 應用濾波
                wrist_angle = int(self.wrist_filter.update(wrist_angle_raw))

        return annotated_frame, [wrist_angle, elbow_angle, aperture_binary, aperture_raw]

def get_only_wrist_angle(detector, img):
    # 此函式現在僅為相容性保留，實際上 main.py 應改用 process_frame
    _, angles = detector.process_frame(img)
    return angles[0]
