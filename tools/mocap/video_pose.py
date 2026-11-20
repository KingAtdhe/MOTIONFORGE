"""Offline tooling: track one person in a video with MediaPipe Pose Landmarker (heavy) and save the landmarks.

Usage: python video_pose.py MODEL.task VIDEO.mp4 OUT.npz [--max-side 1280]
Saves: world (F,33,3) metres, hip-centred, MediaPipe axes (x right, y down, z away from camera);
       image (F,33,3) normalised x,y,z; vis (F,33) visibility; ok (F,) a pose was found; fps.
Runs on a workstation only; nothing here ships in the app and no frames are stored."""
import argparse
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

ap = argparse.ArgumentParser()
ap.add_argument("model"); ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--max-side", type=int, default=1280)
a = ap.parse_args()
cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
opts = PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=a.model), running_mode=RunningMode.VIDEO,
                             num_poses=1, min_pose_detection_confidence=0.5, min_tracking_confidence=0.5)
W, I, V, OK = [], [], [], []
with PoseLandmarker.create_from_options(opts) as lm:
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        h, w = fr.shape[:2]
        s = a.max_side / max(h, w)
        if s < 1:
            fr = cv2.resize(fr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        r = lm.detect_for_video(img, int(round(i * 1000 / fps)))
        if r.pose_world_landmarks:
            wl, il = r.pose_world_landmarks[0], r.pose_landmarks[0]
            W.append([[p.x, p.y, p.z] for p in wl]); I.append([[p.x, p.y, p.z] for p in il])
            V.append([p.visibility for p in il]); OK.append(True)
        else:
            W.append(np.zeros((33, 3))); I.append(np.zeros((33, 3))); V.append(np.zeros(33)); OK.append(False)
        i += 1
np.savez_compressed(a.out, world=np.array(W), image=np.array(I), vis=np.array(V), ok=np.array(OK), fps=fps)
print(a.video.split("/")[-1], "frames", i, "tracked", int(np.sum(OK)), "fps", round(fps, 2))
