import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from ultralytics import YOLO
from moviepy import VideoFileClip
import os
import time
import shutil
from collections import defaultdict
from datetime import datetime
import re

def cv2AddChineseText(img, text, position, textColor, textSize):
    if (isinstance(img, np.ndarray)):  # 判断是否OpenCV图片类型
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    fontStyle = ImageFont.truetype(
        "微软雅黑.TTC", textSize, encoding="utf-8")
    # 绘制文本
    draw.text(position, text, textColor, font=fontStyle)
    # 转换回OpenCV格式
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

# 新增函数：获取下一个输出文件夹路径
def get_next_output_folder(base_path):
    """在基础路径下找到最大序号并返回下一个输出文件夹路径"""
    os.makedirs(base_path, exist_ok=True)
    
    # 查找已存在的output文件夹
    existing_folders = [f for f in os.listdir(base_path) 
                       if os.path.isdir(os.path.join(base_path, f)) 
                       and re.match(r'output\d+', f)]
    
    # 提取数字并找到最大值
    max_num = 0
    for folder in existing_folders:
        try:
            num = int(re.search(r'output(\d+)', folder).group(1))
            if num > max_num:
                max_num = num
        except:
            continue
    
    # 创建新的输出文件夹
    next_num = max_num + 1
    new_folder = os.path.join(base_path, f"output{next_num}")
    os.makedirs(new_folder, exist_ok=True)
    print(f"创建新的输出文件夹: {new_folder}")
    return new_folder

def detect_and_save_segments(
    input_video_path,
    output_folder,
    target_classes,
    pre_buffer_sec=2,
    post_buffer_sec=3,
    conf_threshold=0.25,
    min_segment_duration=0.3
):
    os.makedirs(output_folder, exist_ok=True)
    model = YOLO("./weights/su-v3.pt")
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {input_video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"视频信息: {width}x{height}, {fps:.2f} FPS, 时长: {duration:.2f}秒")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_folder, f"{'-'.join(target_classes)}_visulize_{timestamp}.mp4")
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    # 获取目标类别ID
    class_names = model.names
    target_class_ids = [cid for cid, name in class_names.items() if name.lower() in [cls.lower() for cls in target_classes]]
    if not target_class_ids:
        raise ValueError(f"未找到目标类别: {target_classes}")
    print(f"检测类别: {target_classes} (IDs: {target_class_ids})")

    all_segments = []
    in_segment = False
    segment_start_time = 0

    last_log_time = time.time()

    for frame_idx in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        if current_time - last_log_time > 5:
            print(f"处理进度: {(frame_idx / total_frames) * 100:.1f}% ({frame_idx}/{total_frames})")
            last_log_time = current_time

        current_time_sec = frame_idx / fps
        results = model.predict(frame, conf=conf_threshold, verbose=False)
        detections = results[0].boxes.data.cpu().numpy()

        has_target = False
        area = 0
        for det in detections:
            if len(det) >= 6 and int(det[5]) in target_class_ids:
                has_target = True
                x1, y1, x2, y2 = map(int, det[:4])
                # print("x1, y1, x2, y2:", x1, y1, x2, y2)
                area += (x2 - x1) * (y2 - y1)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # 改为绿色框
                cv2.putText(frame, class_names[int(det[5])], (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                

        # 判断是否进入或离开一个目标片段
        if has_target and not in_segment:
            segment_start_time = current_time_sec
            in_segment = True
        elif not has_target and in_segment:
            segment_end_time = current_time_sec
            if segment_end_time - segment_start_time >= min_segment_duration:
                all_segments.append((segment_start_time, segment_end_time))
            in_segment = False

        # 实时显示统计信息
        target_duration = sum(end - start for start, end in all_segments)
        duration_ratio = (target_duration / duration) * 100 if duration > 0 else 0
        
        frame = cv2AddChineseText(frame, f"广告出现次数(Segments): {len(all_segments)}", (10, 50), (255, 0, 0), 40)
        frame = cv2AddChineseText(frame, f"广告出现时长(Time): {target_duration:.1f}s", (10, 100), (255, 0, 0), 40)
        frame = cv2AddChineseText(frame, f"广告出现时长占比(Time Ratio): {duration_ratio:.2f}%", (10, 150), (255, 0, 0), 40)
        # print("area,width,height:", area/(width*height))
        frame = cv2AddChineseText(frame, f"广告面积占比: {area/(width*height)*100:.1f}%", (10, 200), (255, 0, 0), 40)

        writer.write(frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 如果视频结束时还处于一个片段中，记得加上
    if in_segment:
        if current_time_sec - segment_start_time >= min_segment_duration:
            all_segments.append((segment_start_time, current_time_sec))

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    if not all_segments:
        print(f"未检测到目标类别: {target_classes}")
        return 0.0, [], duration

    # 保存视频片段
    video_clip = VideoFileClip(input_video_path)
    saved_segments = []

    seg_output_folder = os.path.join(output_folder, f"{'-'.join(target_classes)}_segments")   
    os.makedirs(seg_output_folder, exist_ok=True)

    for i, (start, end) in enumerate(all_segments):
        expanded_start = max(0, start - pre_buffer_sec)
        expanded_end = min(duration, end + post_buffer_sec)
        
        try:
            # 修复方法名：subclipped -> subclip
            segment_clip = video_clip.subclipped(expanded_start, expanded_end)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{'-'.join(target_classes)}_{timestamp}_{i+1}_{expanded_start:.1f}s-{expanded_end:.1f}s.mp4"
            output_path = os.path.join(seg_output_folder, output_filename)
            
            # 关键修复：禁用音频处理
            segment_clip.write_videofile(
                output_path, 
                codec="libx264", 
                audio=False,  # 禁用音频
                fps=fps, 
                logger=None
            )
            segment_clip.close()

            saved_segments.append({
                "path": output_path,
                "original_start": start,
                "original_end": end,
                "expanded_start": expanded_start,
                "expanded_end": expanded_end,
                "duration": expanded_end - expanded_start
            })

            print(f"保存片段 {i+1}: {output_filename} ({expanded_end - expanded_start:.1f}秒)")
        except Exception as e:
            print(f"保存片段 {i+1} 时出错: {str(e)}")
            continue

    video_clip.close()
    
    # 计算目标总时长
    target_duration = sum(end - start for start, end in all_segments)
    
    print(f"目标 '{'-'.join(target_classes)}' 总出现时长: {target_duration:.2f}秒")
    print(f"共保存 {len(saved_segments)} 个片段到 {output_folder}")
    return target_duration, saved_segments, duration

def generate_summary_report(target_classes, total_duration, segments, output_folder, duration):
    """生成摘要报告"""
    report_path = os.path.join(output_folder, f"{'-'.join(target_classes)}_summary.txt")
    
    with open(report_path, "w") as f:
        f.write(f"目标类别: {', '.join(target_classes)}\n")
        f.write(f"总出现时长: {total_duration:.2f}秒\n")
        f.write(f"检测到的片段数: {len(segments)}\n\n")
        f.write("各片段详情:\n")
        
        for i, seg in enumerate(segments):
            f.write(f"\n片段 {i+1}:\n")
            f.write(f"  文件路径: {seg['path']}\n")
            f.write(f"  原始时间: {seg['original_start']:.1f}s - {seg['original_end']:.1f}s "
                    f"(时长: {seg['original_end'] - seg['original_start']:.1f}s)\n")
            f.write(f"  扩展时间: {seg['expanded_start']:.1f}s - {seg['expanded_end']:.1f}s "
                    f"(时长: {seg['duration']:.1f}s)\n")
        
        # 计算目标时长占比
        duration_ratio = (total_duration / duration) * 100 if duration > 0 else 0
        
        f.write(f"\n目标出现时长占比: {duration_ratio:.2f}%\n")
    
    print(f"已生成摘要报告: {report_path}")
    return report_path

if __name__ == "__main__":
    # 示例用法
    input_video = "test/广告2.mp4"
    base_output_folder = "output"  # 基础输出目录
    target_classes = ["Billboard", "drinks"]  # 要检测的多个目标类别
    
    # 获取下一个输出文件夹
    output_folder = get_next_output_folder(base_output_folder)
    
    start_time = time.time()
    
    # 检测并保存片段
    total_duration, saved_segments, duration = detect_and_save_segments(
        input_video,
        output_folder,
        target_classes,
        pre_buffer_sec=2,  # 目标出现前保留2秒
        post_buffer_sec=3,  # 目标消失后保留3秒
        min_segment_duration=0.5  # 明确指定最小片段持续时间
    )
    
    # 生成摘要报告
    if saved_segments:
        generate_summary_report(target_classes, total_duration, saved_segments, output_folder, duration)
    
    print(f"处理完成! 总耗时: {time.time() - start_time:.2f}秒")
    print(f"目标 '{', '.join(target_classes)}' 总出现时长: {total_duration:.2f}秒")