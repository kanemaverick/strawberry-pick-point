import os, hashlib
from collections import defaultdict

path = r"C:\Users\xzKan\Desktop\机械臂草莓\pose_annotation_images"
files = [f for f in os.listdir(path) if f.lower().endswith(".jpg")]

hashes = defaultdict(list)
for f in files:
    with open(os.path.join(path, f), "rb") as fp:
        h = hashlib.md5(fp.read()).hexdigest()
    hashes[h].append(f)

exact_dupes = {h: v for h, v in hashes.items() if len(v) > 1}
print(f"总图片数: {len(files)}")
print(f"完全相同（MD5一致）的重复组数: {len(exact_dupes)}")
if exact_dupes:
    for h, names in list(exact_dupes.items())[:5]:
        print(f"  重复组: {names}")
else:
    print("没有完全相同的重复图片")
    print('-> 你看到的"重复"是原始数据集的视频相邻帧，内容极相似但不完全一样')
