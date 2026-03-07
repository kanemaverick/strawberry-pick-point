from ultralytics import FastSAM


def export_lightweight_sam():
    print("正在下载并加载轻量级 FastSAM 模型...")
    # 使用 FastSAM-s (参数量约 11M，完美匹配您 PPT 中对 "EfficientSAM 参数量仅 10M" 的描述)
    # FastSAM 是基于 YOLOv8 的架构，导出过程非常稳定且支持 BBox prompt
    model = FastSAM("FastSAM-s.pt")

    print("正在导出 FastSAM 到 OpenVINO 格式...")
    # 导出为 OpenVINO FP16 格式 (边缘端推荐)
    model.export(format="openvino", half=True)

    print("FastSAM 导出成功！")


if __name__ == "__main__":
    export_lightweight_sam()
