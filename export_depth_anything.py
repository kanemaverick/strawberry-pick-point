import torch
import openvino as ov
from transformers import AutoModelForDepthEstimation


def export_depth_anything_v2():
    print("正在从 Hugging Face 下载并加载 Depth Anything V2 Small (24.8M) 模型...")
    # 这里使用的是 Hugging Face 上官方转换后的 V2 Small 模型
    model_id = "depth-anything/Depth-Anything-V2-Small-hf"
    model = AutoModelForDepthEstimation.from_pretrained(model_id)
    model.eval()

    # Depth Anything 默认推荐输入尺寸通常为 518x518 或 504x504 (ViT patch size 14的倍数)
    # 我们这里使用标准的 1x3x518x518 张量作为 example_input 帮助 OpenVINO 追踪图结构
    dummy_input = torch.randn(1, 3, 518, 518)

    print("正在转换为 OpenVINO 模型并优化图结构...")
    # 将 PyTorch 模型转换为 OpenVINO
    ov_model = ov.convert_model(model, example_input=dummy_input)

    print("正在将模型保存为 FP16 精度的 OpenVINO IR 格式 (适合边缘设备加速)...")
    # 保存为 FP16 精度（大幅减少内存带宽占用，极度适合 NPU/核显，同时不影响深度估计精度）
    ov.save_model(
        ov_model,
        "depth_anything_v2_openvino/depth_anything_v2.xml",
        compress_to_fp16=True,
    )

    print("Depth Anything V2 导出成功！保存路径: depth_anything_v2_openvino/")


if __name__ == "__main__":
    export_depth_anything_v2()
