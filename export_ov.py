from ultralytics import YOLO


import yaml
import os


def export_model():
    print("Loading PyTorch model...")
    # Using the model mentioned in the PPT
    model = YOLO("runs_pose/strawberry_pose_v14/weights/best.pt")

    # Create temp yaml pointing to strawberry_pose_dataset_v2
    temp_yaml = "temp_export.yaml"
    with open("autodl_scripts/strawberry_pose_local.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["path"] = os.path.abspath("strawberry_pose_dataset_v2")
    with open(temp_yaml, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    print("Exporting to OpenVINO INT8 format...")
    # Export the model with NNCF post-training quantization
    model.export(format="openvino", int8=True, data=temp_yaml, device="cpu")
    print("Export completed successfully.")


if __name__ == "__main__":
    export_model()
