# evaluate_model.py
import os
from ultralytics import YOLO

def evaluate():
    print("=== 开始进行模型验证与预测 ===")
    
    # 1. 加载你刚刚训练出来的最强权重 best.pt
    # 请确保路径与你在 train.py 里设置的一致
    best_weights_path = "/root/autodl-tmp/runs/strawberry_detect/weights/best.pt"
    if not os.path.exists(best_weights_path):
        print(f"找不到权重文件 {best_weights_path}，请确认训练是否成功。")
        return
        
    model = YOLO(best_weights_path)

    # 2. 进行验证集验证（会自动生成混淆矩阵、PR曲线等）
    print(">>> 正在在验证集上评估 mAP...")
    metrics = model.val(project="/root/autodl-tmp/runs/eval", name="val_results")
    print(f"验证集 mAP50-95: {metrics.box.map}")
    print(f"验证集 mAP50: {metrics.box.map50}")

    # 3. 对部分高难度图片进行预测可视化（失败/成功样本对比）
    # 这里默认在验证集中随机挑图，如果你有专用的测试集，可以把路径改为测试集的路径
    test_img_dir = "/root/autodl-tmp/strawberry-dataset-for-object-detection-DatasetNinja/val/images" 
    
    if os.path.exists(test_img_dir):
        # 取前 15 张图片作为展示
        test_imgs = [os.path.join(test_img_dir, f) for f in os.listdir(test_img_dir) if f.endswith(('.jpg', '.png'))][:15]
        
        if test_imgs:
            print(f">>> 正在预测 {len(test_imgs)} 张图片以生成对比图...")
            # conf=0.5: 置信度>50%才画框
            # save=True: 保存画上框的预测结果
            model.predict(
                test_imgs, 
                conf=0.5, 
                save=True, 
                project="/root/autodl-tmp/runs/eval", 
                name="predict_vis"
            )
            print("预测完成！可视化结果保存在 /root/autodl-tmp/runs/eval/predict_vis 文件夹下。")
            print("您可以下载这些图片，与原图进行比对，写进报告的'成功/失败可视化对比图'章节。")
    else:
        print(f"找不到图像目录 {test_img_dir}，跳过预测步骤。")

if __name__ == '__main__':
    evaluate()
