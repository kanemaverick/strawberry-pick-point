# pretrained/

本目录存储 **预训练权重**，通过 Git LFS 管理（`.gitattributes` 已配置 `*.pt filter=lfs`）。

## 文件说明

| 文件 | 来源 | 说明 |
|---|---|---|
| `yolo11n-pose.pt` | Ultralytics 官方 | YOLOv11n-Pose 预训练权重，用于 fine-tune |
| `yolo26n.pt` | Ultralytics 官方 | YOLOv8n 检测预训练权重（早期实验用，当前不使用） |

## 下载（如 LFS 未拉取）

```bash
git lfs pull
```

或从 Ultralytics 官方直接下载：

```python
from ultralytics import YOLO
model = YOLO("yolo11n-pose.pt")  # 自动下载到当前目录
```
