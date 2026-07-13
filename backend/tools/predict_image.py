"""
单张/批量图像推理工具

用法：
    python tools/predict_image.py --image test.jpg --weights models/best.pt
    python tools/predict_image.py --dir images/ --weights models/best.pt --conf 0.35
"""
import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True, help="模型路径")
    parser.add_argument("--image", help="单张图片")
    parser.add_argument("--dir", help="图片目录")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    args = parser.parse_args()

    model = YOLO(args.weights)

    if args.image:
        results = model(args.image, conf=args.conf)
        for r in results:
            r.show()         # 弹窗显示
            r.save("predict_output/")  # 保存结果图

    if args.dir:
        results = model(args.dir, conf=args.conf)
        for r in results:
            r.save("predict_output/")


if __name__ == "__main__":
    main()
