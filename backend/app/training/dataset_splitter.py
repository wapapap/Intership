"""
数据集划分与目录组织工具

职责：
  - 将图像和标注文件按指定比例划分到 train/val/test 目录
  - 自动创建目录结构
  - 验证图像与标注的配对完整性

使用方式：
  from app.training.dataset_splitter import DatasetSplitter

  splitter = DatasetSplitter()
  splitter.organize_dataset(
      image_dir="datasets/rsod/raw/images",
      label_dir="datasets/rsod/raw/annotations",
      output_dir="datasets/rsod/yolo_dataset",
      train_ratio=0.8,
      val_ratio=0.1,
      test_ratio=0.1
  )
"""

import random
import shutil
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


class DatasetSplitter:
    """数据集划分与目录组织工具"""

    @staticmethod
    def organize_dataset(
        image_dir: str,
        label_dir: str,
        output_dir: str,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> dict:
        """
        将图像和标注文件按比例划分到 train/val/test 目录

        支持两种模式：
        模式1（推荐）：从原始目录划分，image_dir 直接包含图片文件
        模式2：从已划分目录整理，image_dir 包含 train/val/test 子目录

        Args:
            image_dir: 图像目录（原始目录或已划分目录）
            label_dir: 标注目录（原始目录或已划分目录）
            output_dir: 输出目录（将创建标准 YOLO 目录结构）
            train_ratio: 训练集比例
            val_ratio: 验证集比例
            test_ratio: 测试集比例
            seed: 随机种子（确保可重复）

        Returns:
            划分统计信息（始终包含 train/val/test 键）
        """
        random.seed(seed)

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        image_dir_path = Path(image_dir)

        # 检测模式：检查是否包含 train/val/test 子目录
        subdirs = {d.name for d in image_dir_path.iterdir() if d.is_dir()}
        has_split_subdirs = {"train", "test"}.issubset(subdirs) and (
            "val" in subdirs or "valid" in subdirs
        )

        if has_split_subdirs:
            # 模式2：从已划分目录整理
            logger.info("检测到已划分目录结构，直接整理...")
            return DatasetSplitter._organize_from_split_dirs(
                image_dir, label_dir, output_dir
            )
        else:
            # 模式1：从原始目录划分
            image_files = sorted(
                [
                    f
                    for f in image_dir_path.iterdir()
                    if f.suffix.lower() in image_extensions
                ]
            )

            if not image_files:
                logger.error("图像目录 %s 下未找到图像文件", image_dir)
                return {"train": 0, "val": 0, "test": 0, "missing_labels": [], "error": "未找到图像文件"}

            logger.info("找到 %d 张图像，使用分层采样划分...", len(image_files))

            # 分层采样：为每张图片确定分层键（稀有类优先，确保类别均衡）
            image_strata = DatasetSplitter._compute_strata(image_files, Path(label_dir))
            splits = DatasetSplitter._stratified_split(
                image_files, image_strata, train_ratio, val_ratio, test_ratio
            )

            stats = {"train": 0, "val": 0, "test": 0, "missing_labels": []}

            for split_name, files in splits.items():
                img_out = Path(output_dir) / "images" / split_name
                lbl_out = Path(output_dir) / "labels" / split_name
                img_out.mkdir(parents=True, exist_ok=True)
                lbl_out.mkdir(parents=True, exist_ok=True)

                for img_file in files:
                    shutil.copy2(img_file, img_out / img_file.name)

                    label_file = Path(label_dir) / f"{img_file.stem}.txt"
                    if label_file.exists():
                        shutil.copy2(label_file, lbl_out / label_file.name)
                        stats[split_name] += 1
                    else:
                        empty_label = lbl_out / f"{img_file.stem}.txt"
                        empty_label.touch()
                        stats["missing_labels"].append(img_file.name)
                        stats[split_name] += 1
                        logger.warning(
                            "图像 %s 无对应标注文件，已创建空标注", img_file.name
                        )

            logger.info(
                "数据集划分完成：train=%d, val=%d, test=%d, 缺失标注=%d",
                stats["train"],
                stats["val"],
                stats["test"],
                len(stats["missing_labels"]),
            )
            return stats

    @staticmethod
    def _compute_strata(image_files: list, label_dir: Path) -> dict:
        """
        为每张图片计算分层键，优先使用该图片中最稀有的类别。

        对于多标签图片，以全局出现频率最低的类别作为分层键，
        确保稀有类在各 split 中均匀分布。
        """
        # 第一遍：统计全局类别频率
        class_counts: dict[int, int] = {}
        image_classes: dict[str, list[int]] = {}

        for img_file in image_files:
            label_file = label_dir / f"{img_file.stem}.txt"
            classes = []
            if label_file.exists():
                try:
                    for line in label_file.read_text(encoding="utf-8").strip().split("\n"):
                        parts = line.split()
                        if parts:
                            classes.append(int(parts[0]))
                except Exception:
                    pass
            # 去重
            classes = list(set(classes)) if classes else [-1]
            image_classes[img_file.name] = classes
            for c in classes:
                if c >= 0:
                    class_counts[c] = class_counts.get(c, 0) + 1

        # 第二遍：选每张图的最稀有类作为分层键
        strata: dict[str, int] = {}
        for name, classes in image_classes.items():
            valid = [c for c in classes if c >= 0]
            if valid:
                strata[name] = min(valid, key=lambda c: class_counts.get(c, 0))
            else:
                strata[name] = -1  # 无标签图片归为一组

        return strata

    @staticmethod
    def _stratified_split(
        image_files: list,
        strata: dict,
        train_ratio: float,
        val_ratio: float,
        test_ratio: float,
    ) -> dict:
        """按分层键分组后，每组内按比例分配，保证各类别均衡分布。"""
        from collections import defaultdict

        groups: dict[int, list] = defaultdict(list)
        for img_file in image_files:
            key = strata.get(img_file.name, -1)
            groups[key].append(img_file)

        train_list, val_list, test_list = [], [], []

        for key, files in groups.items():
            random.shuffle(files)
            n = len(files)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)

            train_list.extend(files[:train_end])
            val_list.extend(files[train_end:val_end])
            test_list.extend(files[val_end:])

        # 打乱每个 split 内部顺序，避免同类别图片聚集
        for lst in [train_list, val_list, test_list]:
            random.shuffle(lst)

        return {"train": train_list, "val": val_list, "test": test_list}

    @staticmethod
    def _resolve_split_dir(base_dir: Path, split_name: str) -> Path | None:
        """解析实际的源目录名，兼容 Roboflow 的 'valid' 命名"""
        candidates = [split_name]
        if split_name == "val":
            candidates.append("valid")
        for name in candidates:
            candidate = base_dir / name
            # 检查目录本身，或其下的 images 子目录（Roboflow 格式）
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _find_image_files(src_dir: Path, extensions: set) -> list:
        """在目录中查找图片文件，支持 Roboflow 的 images/ 子目录"""
        # 先检查目录下是否有 images 子目录（Roboflow 格式）
        images_subdir = src_dir / "images"
        search_dir = images_subdir if images_subdir.exists() else src_dir
        return [
            f for f in search_dir.iterdir()
            if f.suffix.lower() in extensions
        ]

    @staticmethod
    def _organize_from_split_dirs(image_dir: str, label_dir: str, output_dir: str) -> dict:
        """
        从已划分的目录结构中整理数据，兼容 Roboflow 格式（valid 命名、images/ 子目录）
        """
        stats = {"train": 0, "val": 0, "test": 0, "missing_labels": []}
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

        for split_name in ["train", "val", "test"]:
            src_img_base = DatasetSplitter._resolve_split_dir(Path(image_dir), split_name)
            src_lbl_base = DatasetSplitter._resolve_split_dir(Path(label_dir), split_name)

            dst_img_dir = Path(output_dir) / "images" / split_name
            dst_lbl_dir = Path(output_dir) / "labels" / split_name

            dst_img_dir.mkdir(parents=True, exist_ok=True)
            dst_lbl_dir.mkdir(parents=True, exist_ok=True)

            if src_img_base is None:
                logger.warning("源目录 %s/%s 不存在，跳过", image_dir, split_name)
                continue

            image_files = DatasetSplitter._find_image_files(src_img_base, image_extensions)

            for img_file in image_files:
                shutil.copy2(img_file, dst_img_dir / img_file.name)

                label_file = None
                if src_lbl_base:
                    # 查找标注文件：先尝试 labels/ 子目录（Roboflow 格式），再尝试同级
                    for lbl_subdir in [src_lbl_base / "labels", src_lbl_base]:
                        candidate = lbl_subdir / f"{img_file.stem}.txt"
                        if candidate.exists():
                            label_file = candidate
                            break

                if label_file:
                    shutil.copy2(label_file, dst_lbl_dir / label_file.name)
                    stats[split_name] += 1
                else:
                    empty_label = dst_lbl_dir / f"{img_file.stem}.txt"
                    empty_label.touch()
                    stats["missing_labels"].append(img_file.name)
                    stats[split_name] += 1
                    logger.warning(
                        "图像 %s 无对应标注文件，已创建空标注", img_file.name
                    )

        logger.info(
            "数据集整理完成：train=%d, val=%d, test=%d, 缺失标注=%d",
            stats["train"],
            stats["val"],
            stats["test"],
            len(stats["missing_labels"]),
        )
        return stats