# yolo实现速力奥广告时长统计

## 0 Get Start

## 1 模型版本
### 1.1 速力奥
| 日期 |  文件名  | 性能 | 预训练模型  |               备注                | 下载链接                                                     | 数据集链接 |
| :--: | :------: | :--: | :---------: | :-------------------------------: | ------------------------------------------------------------ | :--------: |
| 7.29 | su-v1.pt |      | yolov10n.pt | 速力奥"广告牌+产品"检测模型第一版 | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v1.pt?download=true) |[数据集](https://huggingface.co/datasets/bhsh0112/qiji-adver_detect/tree/suliao)       |
| 7.29 | su-v2.pt |      | yolov10n.pt |       修复了类别缺失的问题        | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v2.pt?download=true) |[数据集](https://huggingface.co/datasets/bhsh0112/qiji-adver_detect/tree/suliao)|
| 8.1  | su-v3.pt |      | yolov10n.pt |      补充类似广告作为负样本       | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v3.pt?download=true) |[数据集](https://huggingface.co/datasets/bhsh0112/qiji-adver_detect/tree/suliao)|
| 8.5  | su-v4.pt |      | yolov10s.pt |           补充长尾场景            | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v4.pt?download=true)|[数据集](https://huggingface.co/datasets/bhsh0112/qiji-adver_detect/tree/suliao)|
### 1.2 小米
| 日期 |  文件名  | 性能 | 预训练模型  |               备注                | 下载链接                                                     | 数据集链接 |
| :--: | :------: | :--: | :---------: | :-------------------------------: | ------------------------------------------------------------ | :--------: |
| 8.7 | xiaomi-v1.pt |      | yolov10s.pt | 小米"广告牌"检测模型第一版 | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/master/su-v1.pt?download=true) |[数据集](https://huggingface.co/datasets/bhsh0112/qiji-adver_detect/tree/xiaomi)|

## 2 环境要求

- Python 3.8+
- 操作系统：Linux/macOS/Windows（推荐 Linux）
- 可选：NVIDIA CUDA 11.x+（用于 GPU 加速训练/推理）
- 系统依赖（推荐安装）：
  - ffmpeg（视频处理，供 `moviepy` 使用）
  - libreoffice（DOCX 转 PDF；`pdf_generate.py` 优先使用）
  - libgl1、libglib2.0-0（OpenCV 运行所需）
  - fonts-dejavu-core（包含 `DejaVuSerif-Bold.ttf` 字体，供中文绘制使用）

Ubuntu/Debian 一键安装示例：

```bash
sudo apt update
sudo apt install -y ffmpeg libreoffice libgl1 libglib2.0-0 fonts-dejavu-core
```

## 3 安装

```bash
git clone <this-repo>
cd adver_detect
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

关于 PyTorch：如需 GPU 版本，请参考官方指引选择与你 CUDA 匹配的安装命令：[PyTorch 安装指南](https://pytorch.org/get-started/locally/)。

## 4 目录结构（关键项）

- `cut.py`：从视频中检测目标，导出可视化视频与片段，并生成 `*_summary.txt` 摘要
- `pdf_generate.py`：基于摘要生成报告（优先 DOCX 模板 → 转 PDF，失败则回退 ReportLab 直接生成 PDF）
- `train.py`：使用 Ultralytics YOLO 进行训练
- `weights/`：预训练或已训练权重（参见上表下载链接）
- `test/template.docx`：报告模板（可自定义）
- `output/`：运行后自动生成的输出目录（例如 `output7/`）

## 5 快速开始

### 5.1 运行检测与裁剪（cut）

`cut.py` 的示例入口在文件底部，默认示例：

```bash
python cut.py
```

运行后将创建形如 `output/outputN/` 的目录：

- `*_visulize_*.mp4`：带检测框的可视化视频
- `*_segments/`：自动裁剪的广告片段集合（禁用音轨，避免环境缺音频编码器报错）
- `*_summary.txt`：统计摘要（供报告生成使用）

如需自定义输入视频或类别，可打开并修改 `cut.py` 中的以下变量：`input_video`、`target_classes`、`base_output_folder` 等。

常见目标类别示例：`["Billboard", "drinks"]`。

### 5.2 基于模板生成 PDF 报告

`pdf_generate.py` 提供命令行用法（程序内也会打印帮助）：

```bash
python pdf_generate.py <input_folder> [output_directory] [--no-template] [--template /abs/path/to/template.docx]
```

示例：

```bash
python pdf_generate.py ./output/output7 --template ./test/template.docx
```

说明：
- 默认优先使用 DOCX 模板生成（依赖 `python-docx` 和本地 `libreoffice/soffice`），随后转为 PDF
- 若系统未安装 LibreOffice，会自动保留 DOCX 并回退到 ReportLab 直接生成 PDF
- 若模板字段无法匹配，程序会尽力填充关键统计项（总时长、平均时长、频次、首次/末次时间点等）

### 5.3 训练

确保 `./data/adver.yaml` 可用，并准备好权重文件（例如 `./weights/yolov10n.pt`）：

```bash
python train.py
```

根据你的硬件和数据规模，适当调整 `epochs`、`batch`、`imgsz` 等参数。

## 6 依赖与版本

项目的 Python 依赖见 `requirements.txt`：

```
ultralytics
opencv-python
numpy
Pillow
moviepy
python-docx
reportlab
imageio-ffmpeg
torch
torchvision
```

备注：
- `torch/torchvision` 建议按官方指引安装与你 CUDA 匹配的版本；如不需要 GPU，可直接安装 CPU 版
- `moviepy` 依赖 `ffmpeg`，上文已给出系统级安装方式
- `pdf` 导出优先调用本地 `libreoffice/soffice`，若未安装将自动回退到 ReportLab 方案
- OpenCV 在某些 Linux 环境需要 `libgl1`、`libglib2.0-0` 等系统库
- 字体：`cut.py` 使用 `DejaVuSerif-Bold.ttf` 绘制中文；ReportLab 若需 CJK 更好显示，可在系统中安装相应中文字体

## 7 常见问题（FAQ）

- 没有生成 PDF？请确认已安装 `libreoffice`；否则程序会退回到 ReportLab 并仍生成 PDF
- 报错 `libGL.so`/`GLX` 相关：安装 `libgl1`、`libglib2.0-0`
- MoviePy 报错找不到 FFMPEG：安装系统级 `ffmpeg` 或确保 `imageio-ffmpeg` 可用
- 模板未正确填充：检查模板表头命名是否与代码中识别逻辑相符（如“总露出时长”“平均每次时长”“露出频次”等）