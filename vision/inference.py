# vision/inference.py
# 草莓采摘点实时推理脚本（Windows 调试版）
# 流程：Orbbec Gemini 335 → 硬件 D2C 对齐 → YOLOv11-Pose 推理 → 采摘点像素 → 3D 反投影 → 相机坐标系 (X,Y,Z) 单位米
#
# 运行方式（Anaconda Prompt，在仓库根目录下执行）：
#   conda activate yolov11
#   python vision/inference.py
#
# 按键：
#   Q / ESC  退出
#   S        保存当前帧截图

import sys
import os
from pathlib import Path
import numpy as np
import cv2
import pyorbbecsdk as ob
from ultralytics import YOLO

# ============================================================
# 配置（使用相对路径，从仓库根目录运行）
_HERE = Path(__file__).parent
WEIGHTS = str(_HERE / "weights" / "strawberry_pose_v14_best.pt")
CONF_THRES = 0.45  # 检测置信度阈值
KP_CONF = 0.5  # 采摘点可见度阈值（kp_conf < 此值则不显示3D坐标）
MIN_DEPTH = 100  # 有效深度最小值 mm（过滤噪声）
MAX_DEPTH = 3000  # 有效深度最大值 mm（Gemini 335 最佳工作范围上限）
DEPTH_SAMPLE_R = 3  # 采摘点深度采样半径（像素），取邻域中位数减少噪声
# ============================================================

ESC_KEY = 27


def get_hw_d2c_config(pipeline: ob.Pipeline) -> ob.Config:
    """配置硬件 D2C（深度对齐到彩色），优先使用 1280x720 RGB"""
    config = ob.Config()
    color_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)

    selected_color = None
    # 优先找 1280x720 RGB，找不到就用默认
    for i in range(len(color_profiles)):
        cp = color_profiles[i]
        if (
            cp.get_format() == ob.OBFormat.RGB
            and cp.get_width() == 1280
            and cp.get_height() == 720
        ):
            selected_color = cp
            break
    if selected_color is None:
        for i in range(len(color_profiles)):
            cp = color_profiles[i]
            if cp.get_format() == ob.OBFormat.RGB:
                selected_color = cp
                break
    if selected_color is None:
        selected_color = color_profiles.get_default_video_stream_profile()

    print(
        f"彩色流：{selected_color.get_width()}x{selected_color.get_height()} "
        f"@ {selected_color.get_fps()}fps  fmt={selected_color.get_format()}"
    )

    # 获取与该彩色分辨率对应的硬件 D2C 深度分辨率
    d2c_depth_list = pipeline.get_d2c_depth_profile_list(
        selected_color, ob.OBAlignMode.HW_MODE
    )
    if len(d2c_depth_list) == 0:
        print("硬件 D2C 不支持当前彩色分辨率，回退到软件对齐")
        # 软件对齐回退
        depth_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
        selected_depth = depth_profiles.get_default_video_stream_profile()
        config.enable_stream(selected_color)
        config.enable_stream(selected_depth)
        config.set_align_mode(ob.OBAlignMode.SW_MODE)
    else:
        selected_depth = d2c_depth_list[0]
        print(
            f"深度流（D2C对齐）：{selected_depth.get_width()}x{selected_depth.get_height()} "
            f"@ {selected_depth.get_fps()}fps"
        )
        config.enable_stream(selected_color)
        config.enable_stream(selected_depth)
        config.set_align_mode(ob.OBAlignMode.HW_MODE)

    return config


def frame_to_bgr(frame: ob.VideoFrame) -> np.ndarray:
    """将 Orbbec 彩色帧转为 OpenCV BGR 格式"""
    w, h = frame.get_width(), frame.get_height()
    data = np.asanyarray(frame.get_data())
    fmt = frame.get_format()
    if fmt == ob.OBFormat.RGB:
        img = np.resize(data, (h, w, 3))
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif fmt == ob.OBFormat.BGR:
        return np.resize(data, (h, w, 3))
    elif fmt == ob.OBFormat.MJPG:
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    elif fmt == ob.OBFormat.YUYV:
        img = np.resize(data, (h, w, 2))
        return cv2.cvtColor(img, cv2.COLOR_YUV2BGR_YUYV)
    else:
        print(f"不支持的彩色格式: {fmt}")
        return None


def get_depth_at_point(
    depth_data: np.ndarray, u: int, v: int, r: int = DEPTH_SAMPLE_R
) -> float:
    """
    在 (u, v) 附近 r 像素半径范围内取有效深度中位数（单位 mm）
    有效范围：MIN_DEPTH ~ MAX_DEPTH
    返回 0 表示无效
    """
    h, w = depth_data.shape
    u0, u1 = max(0, u - r), min(w, u + r + 1)
    v0, v1 = max(0, v - r), min(h, v + r + 1)
    roi = depth_data[v0:v1, u0:u1].flatten().astype(np.float32)
    valid = roi[(roi >= MIN_DEPTH) & (roi <= MAX_DEPTH)]
    if len(valid) == 0:
        return 0.0
    return float(np.median(valid))


def pixel_to_camera_xyz(
    u: float,
    v: float,
    depth_mm: float,
    intrinsic: ob.OBCameraIntrinsic,
    extrinsic: ob.OBExtrinsic,
) -> tuple:
    """
    将彩色图像上的像素点 (u, v) + 深度值反投影到相机 3D 坐标系 (X, Y, Z) 单位米
    使用 Orbbec SDK 的 transformation2dto3d，extrinsic 为 depth→color 的外参
    （硬件D2C后深度图已对齐到彩色，所以 extrinsic 传单位矩阵也可以，这里保持严谨）
    """
    point2d = ob.OBPoint2f(float(u), float(v))
    # transformation2dto3d 输入：像素坐标、深度(mm)、内参、外参
    # 外参这里使用彩色到彩色（单位矩阵），因为深度已对齐到彩色坐标系
    point3d = ob.transformation2dto3d(point2d, depth_mm, intrinsic, extrinsic)
    # point3d 单位为 mm，转换为米
    return (point3d.x / 1000.0, point3d.y / 1000.0, point3d.z / 1000.0)


def draw_results(
    img: np.ndarray,
    results,
    depth_data: np.ndarray,
    color_intrinsic: ob.OBCameraIntrinsic,
    depth_to_color_extrinsic: ob.OBExtrinsic,
    depth_scale: float,
) -> np.ndarray:
    """
    在图像上绘制检测结果：BBox + 采摘点 + 3D 坐标
    同时打印每帧的采摘点 3D 坐标（供后续接入 ROS2 使用）
    """
    # 深度数据转换为实际 mm 值
    depth_mm = depth_data.astype(np.float32) * depth_scale

    if results[0].keypoints is None:
        return img

    boxes = results[0].boxes
    kpts = results[0].keypoints

    for i, (box, kp) in enumerate(zip(boxes, kpts.data)):
        conf = float(box.conf[0])
        if conf < CONF_THRES:
            continue

        # --- BBox ---
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 200, 50), 2)
        cv2.putText(
            img,
            f"ripe {conf:.2f}",
            (x1, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 200, 50),
            2,
        )

        # --- 采摘点 ---
        # kp shape: [1, 3]  → kp[0] = [kp_x, kp_y, kp_conf]
        kp_x_px = float(kp[0][0])
        kp_y_px = float(kp[0][1])
        kp_c = float(kp[0][2])

        if kp_c < KP_CONF:
            # 可见度不足，只标 BBox 不标点
            cv2.putText(
                img,
                "no keypoint",
                (x1, y2 + 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (100, 100, 100),
                1,
            )
            continue

        u, v = int(round(kp_x_px)), int(round(kp_y_px))

        # 防止越界
        h_img, w_img = img.shape[:2]
        u = max(0, min(w_img - 1, u))
        v = max(0, min(h_img - 1, v))

        # --- 几何过滤：采摘点必须在 BBox 上 2/3 范围内 ---
        # 果梗在草莓上方，合理的采摘点不会落在 BBox 下 1/3
        # 如果模型预测点在 BBox 下半部，说明预测偏差大，跳过不显示
        box_h = y2 - y1
        upper_limit = y1 + int(box_h * 0.75)  # BBox 上 75% 处
        if v > upper_limit:
            cv2.putText(
                img,
                "kp filtered",
                (x1, y2 + 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (128, 128, 0),
                1,
            )
            continue

        # 读取深度
        d_mm = get_depth_at_point(depth_mm.astype(np.float32), u, v)

        # 画采摘点
        cv2.circle(img, (u, v), 6, (0, 0, 255), -1)  # 红色实心圆
        cv2.circle(img, (u, v), 10, (255, 255, 255), 2)  # 白色外圈

        if d_mm > 0:
            # 2D → 3D 反投影
            X, Y, Z = pixel_to_camera_xyz(
                u, v, d_mm, color_intrinsic, depth_to_color_extrinsic
            )
            coord_text = f"({X:.3f}, {Y:.3f}, {Z:.3f})m"
            cv2.putText(
                img,
                coord_text,
                (u + 12, v),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )
            # 终端输出（后续 ROS2 节点会改为 publish）
            print(
                f"  草莓{i + 1} 采摘点像素({u},{v}) 深度{d_mm:.0f}mm → 相机坐标 X={X:.4f} Y={Y:.4f} Z={Z:.4f} m"
            )
        else:
            cv2.putText(
                img,
                "depth=0",
                (u + 12, v),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (128, 128, 0),
                1,
            )
            print(f"  草莓{i + 1} 采摘点像素({u},{v}) 深度无效（超出范围或遮挡）")

    return img


def main():
    print("=== 草莓采摘点推理（Orbbec Gemini 335 + YOLOv11-Pose）===")

    # 检查权重文件
    if not os.path.exists(WEIGHTS):
        print(f"错误：找不到权重文件 {WEIGHTS}")
        print("请确认训练已完成，或修改脚本顶部的 WEIGHTS 路径")
        sys.exit(1)

    # 加载模型
    print(f"加载模型：{WEIGHTS}")
    model = YOLO(WEIGHTS)
    print("模型加载完成")

    # 初始化相机
    print("初始化 Orbbec Gemini 335...")
    pipeline = ob.Pipeline()

    try:
        pipeline.enable_frame_sync()
    except Exception as e:
        print(f"帧同步设置失败（非致命）: {e}")

    config = get_hw_d2c_config(pipeline)
    pipeline.start(config)
    print("相机启动成功")

    # 获取相机内参（彩色相机）和外参（用于反投影）
    # 等第一帧到来后再读取内参
    color_intrinsic = None
    depth_to_color_extrinsic = None
    depth_scale = 1.0  # 深度缩放因子（raw值 × scale = mm）

    save_count = 0
    print("\n开始推理... 按 Q/ESC 退出，按 S 保存截图\n")

    while True:
        frames = pipeline.wait_for_frames(1000)
        if frames is None:
            continue

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if color_frame is None or depth_frame is None:
            continue

        # 第一帧时读取内参和外参
        if color_intrinsic is None:
            try:
                color_profile = (
                    color_frame.get_stream_profile().as_video_stream_profile()
                )
                depth_profile = (
                    depth_frame.get_stream_profile().as_video_stream_profile()
                )
                color_intrinsic = color_profile.get_intrinsic()
                # 硬件 D2C 后深度已经对齐到彩色坐标系
                # extrinsic: depth → color（transformation2dto3d 内部会用到）
                depth_to_color_extrinsic = depth_profile.get_extrinsic_to(color_profile)
                depth_scale = depth_frame.get_depth_scale()
                print(
                    f"彩色内参：fx={color_intrinsic.fx:.2f} fy={color_intrinsic.fy:.2f} "
                    f"cx={color_intrinsic.cx:.2f} cy={color_intrinsic.cy:.2f}"
                )
                print(f"深度缩放因子：{depth_scale}  (raw * {depth_scale} = mm)")
            except Exception as e:
                print(f"读取内参失败: {e}")
                continue

        # 转换彩色帧
        img_bgr = frame_to_bgr(color_frame)
        if img_bgr is None:
            continue

        # 深度数据（raw uint16，需乘 depth_scale 才是 mm）
        dw = depth_frame.get_width()
        dh = depth_frame.get_height()
        depth_raw = np.frombuffer(depth_frame.get_data(), dtype=np.uint16).reshape(
            dh, dw
        )

        # 深度图尺寸应与彩色图一致（硬件 D2C 保证），如果不一致则 resize
        ih, iw = img_bgr.shape[:2]
        if depth_raw.shape != (ih, iw):
            depth_raw = cv2.resize(depth_raw, (iw, ih), interpolation=cv2.INTER_NEAREST)

        # YOLOv11-Pose 推理
        results = model(img_bgr, conf=CONF_THRES, verbose=False)

        # 绘制结果 + 计算3D坐标
        vis = draw_results(
            img_bgr.copy(),
            results,
            depth_raw,
            color_intrinsic,
            depth_to_color_extrinsic,
            depth_scale,
        )

        # 显示
        cv2.namedWindow("草莓采摘点推理", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("草莓采摘点推理", 960, 540)
        cv2.imshow("草莓采摘点推理", vis)

        key = cv2.waitKey(1) & 0xFF
        if key in (ESC_KEY, ord("q"), ord("Q")):
            break
        elif key in (ord("s"), ord("S")):
            save_path = f"capture_{save_count:04d}.jpg"
            cv2.imwrite(save_path, vis)
            print(f"截图保存：{save_path}")
            save_count += 1

    cv2.destroyAllWindows()
    pipeline.stop()
    print("已退出")


if __name__ == "__main__":
    main()
