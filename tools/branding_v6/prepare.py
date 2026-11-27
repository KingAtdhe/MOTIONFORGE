"""MOTIONFORGE icon & launch screen v6, step 1: the owner's flexing-poses sheet -> four high-resolution cut-outs.

Source: assets/branding/v6/flexing_poses_sheet.png (the owner's art, 1536x1024).
Crops the male and female close-up portraits and full-body front double-biceps poses, upscales each 4x with
EDSR (OpenCV dnn_superres; model EDSR_x4.pb from github.com/Saafke/EDSR_Tensorflow) and cuts the figure out with
rembg (isnet-general-use + alpha matting). Writes <work>/<name>_cut.png.

Needs: pip install "opencv-contrib-python-headless<5" "rembg[cpu]" pillow numpy
Usage: python tools/branding_v6/prepare.py <EDSR_x4.pb> <work_dir>
"""
import os, sys
import cv2
from cv2 import dnn_superres
from PIL import Image
from rembg import new_session, remove

CROPS = {'m_bust': (915, 40, 1345, 488), 'f_bust': (915, 525, 1345, 1000), 'm_front': (25, 35, 285, 462), 'f_front': (25, 525, 285, 965)}
model, work = sys.argv[1:3]
os.makedirs(work, exist_ok=True)
sheet = Image.open(os.path.join(os.path.dirname(__file__), '../../assets/branding/v6/flexing_poses_sheet.png')).convert('RGB')
sr = dnn_superres.DnnSuperResImpl_create(); sr.readModel(model); sr.setModel('edsr', 4)
seg = new_session('isnet-general-use')
for name, box in CROPS.items():
    p = os.path.join(work, name + '.png'); sheet.crop(box).save(p)
    up = sr.upsample(cv2.imread(p)); cv2.imwrite(os.path.join(work, name + '_x4.png'), up)
    cut = remove(Image.open(os.path.join(work, name + '_x4.png')), session=seg, alpha_matting=True,
                 alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=15, alpha_matting_erode_size=12)
    cut.save(os.path.join(work, name + '_cut.png')); print(name, cut.size, flush=True)
