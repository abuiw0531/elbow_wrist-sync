import pybullet as p
import pybullet_data
import time
import math
import os

class PyBulletSim:
    def __init__(self, urdf_path="assets/simple_arm.urdf"):
        # 連接 PyBullet (GUI 模式)
        self.physicsClient = p.connect(p.GUI)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        
        # 設定重力與基礎視角 (從正側面看較清楚)
        p.setGravity(0, 0, -9.81)
        p.resetDebugVisualizerCamera(cameraDistance=1.5, cameraYaw=90, cameraPitch=-20, cameraTargetPosition=[0, 0, 0.5])
        
        # 載入地面
        self.planeId = p.loadURDF("plane.urdf")
        
        # 載入我們自訂的手臂模型
        # 使用 os.path.dirname(__file__) 確保不管在哪裡執行 main.py，都能找對路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        full_urdf_path = os.path.join(project_root, "assets", "simple_arm.urdf")
            
        try:
            # 計算翻轉 -90 度 (-1.5708 rad) 的四元數，讓整支手臂反方向平躺
            start_orientation = p.getQuaternionFromEuler([0, -1.5708, 0])
            # 高度稍微提升一點 (Z=0.2) 避免和地板穿模
            self.robotId = p.loadURDF(full_urdf_path, basePosition=[0, 0, 0.2], baseOrientation=start_orientation, useFixedBase=True)
            print(f"成功載入 Robot URDF: {full_urdf_path}")
        except Exception as e:
            print(f"無法載入 URDF: {e}")
            self.robotId = None
            return
            
        # 取得所有關節並找出我們定義的關節 ID
        self.joint_indices = {}
        num_joints = p.getNumJoints(self.robotId)
        for i in range(num_joints):
            joint_info = p.getJointInfo(self.robotId, i)
            joint_name = joint_info[1].decode("utf-8")
            self.joint_indices[joint_name] = i
            
            # 初始化為沒有馬達干擾的動力模式，改為由 Position Control 控制
            # 將力矩設回較穩定的值，移除過激的 maxVelocity 避免計算崩潰
            p.setJointMotorControl2(
                bodyIndex=self.robotId,
                jointIndex=i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=0,
                force=1000,          # 再次大幅增強初始穩定扭力
                maxVelocity=15.0     # 大幅增加初始預設速度
            )
            
        print("Joint mapping found:", self.joint_indices)

    def update(self, elbow_angle, wrist_angle, aperture_binary):
        """
        elbow_angle: 0 ~ 180 度 (0 為伸直, 180 為彎曲)
        wrist_angle: 0 ~ 180 度 (90水平, 0上抬, 180下壓)
        aperture_binary: 0 (閉合), 1 (張開)
        """
        if self.robotId is None:
            return

        # 1. 計算轉換
        # 手肘：希望 0 度時手臂是平的。
        # 如果手臂方向與您的動作相反，我們在此加上負號讓它逆轉。
        rad_elbow = -math.radians(elbow_angle) 
        
        # 手腕：希望 90 度時是平的 (手掌與前臂呈一直線)。
        # URDF 初始 (0) 狀態就是直的。因此真實手腕若是 90，URDF 應為 0。
        # 如果手往上抬 (真實數字變小)，就給負的角度讓他往上轉；手往下壓 (數字變大)，就給正的。
        rad_wrist = math.radians(wrist_angle - 90)
        
        # Aperture： 0=閉合(距離0)，1=張開(距離0.04)
        finger_pos = 0.04 if aperture_binary == 1 else 0.0
        
        # 2. 應用位置控制給 PyBullet
        # 再次大幅加速並加強扭力 (力矩加大到 2000，速度拉高到 15)
        arm_force = 2000
        arm_max_vel = 15.0
        
        if "joint_elbow" in self.joint_indices:
            p.setJointMotorControl2(
                bodyIndex=self.robotId,
                jointIndex=self.joint_indices["joint_elbow"],
                controlMode=p.POSITION_CONTROL,
                targetPosition=rad_elbow,
                force=arm_force,
                maxVelocity=arm_max_vel
            )
            
        if "joint_wrist" in self.joint_indices:
            p.setJointMotorControl2(
                bodyIndex=self.robotId,
                jointIndex=self.joint_indices["joint_wrist"],
                controlMode=p.POSITION_CONTROL,
                targetPosition=rad_wrist,
                force=arm_force,
                maxVelocity=arm_max_vel
            )
            
        # 左右手指 (對稱移動)
        if "joint_finger_left" in self.joint_indices:
            p.setJointMotorControl2(
                bodyIndex=self.robotId,
                jointIndex=self.joint_indices["joint_finger_left"],
                controlMode=p.POSITION_CONTROL,
                targetPosition=finger_pos,
                force=arm_force,
                maxVelocity=arm_max_vel
            )
        if "joint_finger_right" in self.joint_indices:
            p.setJointMotorControl2(
                bodyIndex=self.robotId,
                jointIndex=self.joint_indices["joint_finger_right"],
                controlMode=p.POSITION_CONTROL,
                targetPosition=finger_pos,
                force=arm_force,
                maxVelocity=arm_max_vel
            )
            
        # 推動模擬時間前進
        p.stepSimulation()
        
    def disconnect(self):
        p.disconnect()
