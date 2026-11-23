"""Run the app's pose_landmarker_lite.task over a rendered video (frames dir) in VIDEO mode, like the app does.
Writes a compact fixture: one line per frame 't w h' + 33*(x y z vis pres) or 't w h none' when no person."""
import sys, os, glob
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
src, out = sys.argv[1], sys.argv[2]
fps = int(dict(l.strip().split("=", 1) for l in open(os.path.join(src, "meta.txt")) if "=" in l)["fps"])
opts = vision.PoseLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=os.environ.get("POSE_MODEL", "app/src/main/assets/models/pose_landmarker_lite.task")),
                                    running_mode=vision.RunningMode.VIDEO, num_poses=1,
                                    min_pose_detection_confidence=0.5, min_pose_presence_confidence=0.5, min_tracking_confidence=0.5)
lm = vision.PoseLandmarker.create_from_options(opts)
lines, miss = [], 0
for i, f in enumerate(sorted(glob.glob(os.path.join(src, "f*.jpg")))):
    img = mp.Image.create_from_file(f); t = int(round(i * 1000 / fps))
    r = lm.detect_for_video(img, t)
    if not r.pose_landmarks:
        lines.append(f"{t} {img.width} {img.height} none"); miss += 1; continue
    p = r.pose_landmarks[0]
    lines.append(f"{t} {img.width} {img.height} " + " ".join(f"{q.x:.4f} {q.y:.4f} {q.z:.4f} {q.visibility:.3f} {q.presence:.3f}" for q in p))
open(out, "w").write("\n".join(lines) + "\n")
print("LM", out, len(lines), "frames, no person in", miss, flush=True); os._exit(0)
