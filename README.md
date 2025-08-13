# yolo实现速力奥广告时长统计

## 0 Get Start

## 1 模型版本
### 1.1 速力奥
| 日期 |  文件名  | 性能 | 预训练模型  |               备注                | 下载链接                                                     |
| :--: | :------: | :--: | :---------: | :-------------------------------: | ------------------------------------------------------------ |
| 7.29 | su-v1.pt |      | yolov10n.pt | 速力奥“广告牌+产品”检测模型第一版 | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v1.pt?download=true) |
| 7.29 | su-v2.pt |      | yolov10n.pt |       修复了类别缺失的问题        | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v2.pt?download=true) |
| 8.1  | su-v3.pt |      | yolov10n.pt |      补充类似广告作为负样本       | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v3.pt?download=true) |
| 8.5  | su-v4.pt |      | yolov10s.pt |           补充长尾场景            | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/suliao/su-v4.pt?download=true)|
### 1.2 小米
| 日期 |  文件名  | 性能 | 预训练模型  |               备注                | 下载链接                                                     |
| :--: | :------: | :--: | :---------: | :-------------------------------: | ------------------------------------------------------------ |
| 8.7 | xiaomi-v1.pt |      | yolov10s.pt | 小米“广告牌”检测模型第一版 | [下载](https://huggingface.co/bhsh0112/qiji-adver_detect/resolve/master/su-v1.pt?download=true) |
