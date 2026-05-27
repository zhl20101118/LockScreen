import cv2
import numpy as np
import time
import os
import sys
import subprocess
import ctypes
from ctypes import wintypes
from collections import deque

# ------------------------ 模型路径 ------------------------
YUNET_MODEL = "model/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "model/face_recognition_sface_2021dec.onnx"

if not os.path.exists(YUNET_MODEL):
    print(f"[ERROR] 缺少 Yunet 模型: {YUNET_MODEL}")
    sys.exit(1)
if not os.path.exists(SFACE_MODEL):
    print(f"[ERROR] 缺少 SFace 模型: {SFACE_MODEL}")
    sys.exit(1)

# ------------------------ 初始化检测器与特征提取器 ------------------------
detector = cv2.FaceDetectorYN.create(YUNET_MODEL, "", (320, 320))
feature_extractor = cv2.FaceRecognizerSF.create(SFACE_MODEL, "")
print("[INFO] YuNet 检测器 + SFace 特征模型加载成功")

# ------------------------ 人脸对齐函数 ------------------------
def align_face(img, face):
    std_points = np.array([
        [30.2946, 51.6963],   # 左眼
        [65.5318, 51.6963],   # 右眼
        [48.0252, 71.7366],   # 鼻尖
        [33.5493, 92.3655],   # 左嘴角
        [62.7299, 92.3655]    # 右嘴角
    ], dtype=np.float32)

    landmarks = face[4:14].reshape(5, 2).astype(np.float32)
    src_points = np.array([
        landmarks[0],   # 左眼
        landmarks[1],   # 右眼
        landmarks[2],   # 鼻尖
        landmarks[4],   # 左嘴角
        landmarks[3]    # 右嘴角
    ])

    M, _ = cv2.estimateAffine2D(src_points, std_points)
    aligned = cv2.warpAffine(img, M, (112, 112))
    return aligned

# ------------------------ 加载参考人脸特征 ------------------------
def get_ref_feat():
    features = []
    if os.path.exists("my_photo.jpg"):
        img = cv2.imread("my_photo.jpg")
        if img is not None:
            h, w = img.shape[:2]
            detector.setInputSize((w, h))
            result = detector.detect(img)
            if result[1] is not None and result[1].shape[0] > 0:
                face = result[1][0]
                aligned = align_face(img, face)
                feat = feature_extractor.feature(aligned).ravel()
                features.append(feat)
                print("[INFO] 已添加 my_photo.jpg 特征")
    ref_dir = "ref_images"
    if os.path.exists(ref_dir):
        for f in sorted(os.listdir(ref_dir)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(ref_dir, f)
                img = cv2.imread(img_path)
                if img is None: continue
                h, w = img.shape[:2]
                detector.setInputSize((w, h))
                result = detector.detect(img)
                if result[1] is not None and result[1].shape[0] > 0:
                    face = result[1][0]
                    aligned = align_face(img, face)
                    feat = feature_extractor.feature(aligned).ravel()
                    features.append(feat)
    if not features:
        return None
    avg_feat = np.mean(features, axis=0)
    norm = np.linalg.norm(avg_feat)
    if norm > 0:
        avg_feat = avg_feat / norm
    avg_feat = avg_feat.reshape(1, -1)
    print(f"[INFO] 使用 {len(features)} 张照片的平均特征")
    return avg_feat

ref_feat = get_ref_feat()
if ref_feat is None:
    print("[ERROR] 未找到参考人脸")
    sys.exit(1)

THRESHOLD = 0.7

# ------------------------ 点头检测参数 ------------------------
NOD_WINDOW_SEC = 2.0
NOD_DIFF_THRESH = 10.0
ASPECT_RATIO_CHANGE_MAX = 0.1

# ------------------------ 鼠标移动检测（低CPU轮询）-----------------------
user32 = ctypes.windll.user32
point = wintypes.POINT()
last_x, last_y = -1, -1

def mouse_moved():
    global last_x, last_y
    user32.GetCursorPos(ctypes.byref(point))
    if last_x == -1 and last_y == -1:
        last_x, last_y = point.x, point.y
        return False
    moved = (point.x != last_x) or (point.y != last_y)
    last_x, last_y = point.x, point.y
    return moved

# ------------------------ 执行 kill.exe ------------------------
def run_kill_exe():
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    kill_path = os.path.join(base_dir, "kill.exe")
    if not os.path.exists(kill_path):
        kill_path = "kill.exe"   # 尝试当前路径
    try:
        subprocess.run(kill_path, check=False, shell=False)
        print("[INFO] kill.exe 已执行")
        return True
    except Exception as e:
        print(f"[ERROR] 执行 kill.exe 失败: {e}")
        return False

# ------------------------ 输入法切换 ------------------------
def switch_to_sogou_or_ms_pinyin():
    """
    优先切换至搜狗输入法，如果不存在则切换至微软拼音
    """
    def enum_keyboard_layouts():
        num = user32.GetKeyboardLayoutList(0, None)
        if num == 0:
            return []
        hkls = (wintypes.HKL * num)()
        user32.GetKeyboardLayoutList(num, hkls)
        return list(hkls)
    
    layouts = enum_keyboard_layouts()
    for hkl in layouts:
        name_buf = ctypes.create_unicode_buffer(9)
        if user32.GetKeyboardLayoutNameW(name_buf):
            if "sogou" in name_buf.value.lower():
                user32.ActivateKeyboardLayout(hkl, 0)
                print("[INFO] 已切换至搜狗输入法")
                return True
    
    # 没有搜狗，切换到微软拼音
    ms_hkl = user32.LoadKeyboardLayoutW("00000804", 1)
    if ms_hkl:
        user32.ActivateKeyboardLayout(ms_hkl, 0)
        print("[INFO] 已切换至微软拼音输入法")
        return True
    else:
        print("[WARN] 无法切换输入法")
        return False

# ------------------------ 30秒识别窗口 ------------------------
def run_recognition_window():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    start_time = time.time()
    detect_end_time = start_time + 30
    print(f"[INFO] 识别窗口已开启，持续30秒（至 {time.strftime('%H:%M:%S', time.localtime(detect_end_time))}）")
    print("[INFO] 请面对摄像头，做出点头动作（低头再抬头）")
    
    history = deque(maxlen=300)
    verify_frames_left = 0
    
    try:
        while time.time() < detect_end_time:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            
            current_time = time.time()
            h, w = frame.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            
            pitch = None
            aspect_ratio = None
            face = None
            if faces is not None:
                face = faces[0]
                bbox = face[:4].astype(int)
                x, y, w_face, h_face = bbox
                aspect_ratio = w_face / h_face
                pitch = face[5]
                history.append((current_time, pitch, aspect_ratio))
            
            while history and history[0][0] < current_time - NOD_WINDOW_SEC:
                history.popleft()
            
            # 点头检测
            if verify_frames_left == 0 and len(history) >= 5:
                pitches = [p for _, p, _ in history]
                aspects = [a for _, _, a in history]
                pitch_diff = max(pitches) - min(pitches)
                aspect_change = max(aspects) - min(aspects)
                if pitch_diff >= NOD_DIFF_THRESH and aspect_change <= ASPECT_RATIO_CHANGE_MAX:
                    print(f"[{time.strftime('%H:%M:%S')}] 检测到点头 (pitch差值={pitch_diff:.1f})")
                    verify_frames_left = 4
            
            # 验证阶段
            if verify_frames_left > 0 and face is not None:
                aligned = align_face(frame, face)
                feat = feature_extractor.feature(aligned)
                sim = feature_extractor.match(ref_feat, feat, cv2.FaceRecognizerSF_FR_COSINE)
                print(f"[{time.strftime('%H:%M:%S')}] 验证剩余{verify_frames_left}帧，相似度={sim:.3f}")
                if sim >= THRESHOLD:
                    print(f"[{time.strftime('%H:%M:%S')}] 识别成功！相似度 {sim:.3f} ≥ 0.7")
                    return True
                verify_frames_left -= 1
                if verify_frames_left == 0:
                    print("[INFO] 4帧验证结束，未达标，继续等待点头...")
            elif verify_frames_left > 0 and face is None:
                print(f"[{time.strftime('%H:%M:%S')}] 验证帧剩余{verify_frames_left}，未检测到人脸，跳过")
                verify_frames_left -= 1
            
            time.sleep(0.01)
    finally:
        cap.release()
    return False

# ------------------------ 主循环 ------------------------
def main():
    print("[INFO] 程序已启动，移动鼠标将触发30秒人脸识别窗口")
    print("[INFO] 识别成功后先执行 kill.exe，再切换输入法，然后退出")
    print("[INFO] 按 Ctrl+C 退出程序")
    
    while True:
        try:
            if mouse_moved():
                print(f"[{time.strftime('%H:%M:%S')}] 检测到鼠标移动，启动识别窗口")
                success = run_recognition_window()
                if success:
                    # 1. 执行 kill.exe
                    run_kill_exe()
                    # 2. 切换输入法
                    switch_to_sogou_or_ms_pinyin()
                    print("[INFO] 任务完成，程序退出")
                    break
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 30秒内未识别到目标人脸，回到空闲状态，等待下次鼠标移动")
            else:
                time.sleep(0.05)
        except Exception as e:
            print(f"[ERROR] 主循环异常: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断，程序退出")
    finally:
        cv2.destroyAllWindows()

