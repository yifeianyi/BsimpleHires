import subprocess
import os
import threading
from typing import Callable, Optional, List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .ffmpeg_service import FFmpegService
from .settings_service import SettingsService
from utils.logging_utils import get_logger
from utils.path_utils import find_ffmpeg_executable

logger = get_logger(__name__)


class ConversionProgress:
    """转换进度信息类"""
    def __init__(self):
        self.current_file = ""
        self.total_files = 0
        self.completed_files = 0
        self.current_progress = 0.0  # 当前文件进度 0-100
        self.total_progress = 0.0  # 总体进度 0-100
        self.status = "等待中"  # 等待中/转换中/已完成/出错
        self.error_message = ""
        self.active_threads = 0  # 当前活跃线程数
        self.active_file_progresses: list[tuple[str, float]] = []

    def snapshot(self) -> "ConversionProgress":
        snapshot = ConversionProgress()
        snapshot.current_file = self.current_file
        snapshot.total_files = self.total_files
        snapshot.completed_files = self.completed_files
        snapshot.current_progress = self.current_progress
        snapshot.total_progress = self.total_progress
        snapshot.status = self.status
        snapshot.error_message = self.error_message
        snapshot.active_threads = self.active_threads
        snapshot.active_file_progresses = list(self.active_file_progresses)
        return snapshot


class ConverterService:
    """视频转音频服务类，将视频转换为MOV容器下的PCM 24bit音频格式"""
    OUTPUT_SUFFIX = "_bsimple"
    
    @staticmethod
    def _terminate_process(process: subprocess.Popen) -> None:
        process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    @staticmethod
    def _remove_incomplete_output(output_path: str) -> None:
        """Best-effort cleanup for cancelled/failed outputs."""
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
                logger.info("已删除未完成输出: %s", output_path)
        except OSError as exc:
            logger.warning("删除未完成输出失败: %s - %s", output_path, exc)

    @staticmethod
    def build_output_path(input_path: str, output_dir: str) -> str:
        """Build a non-destructive output path with collision handling."""
        settings = SettingsService.load()
        input_name = Path(input_path).stem
        base_name = f"{input_name}{ConverterService.OUTPUT_SUFFIX}"
        candidate = Path(output_dir) / f"{base_name}.mov"

        if settings.naming_strategy == "overwrite":
            return str(candidate)

        suffix = 2

        while candidate.exists():
            candidate = Path(output_dir) / f"{base_name}_{suffix}.mov"
            suffix += 1

        return str(candidate)

    
    @staticmethod
    def convert_to_pcm_mov(input_path: str, output_path: str, 
                          progress_callback: Optional[Callable[[float], None]] = None,
                          error_callback: Optional[Callable[[str], None]] = None,
                          stop_event: Optional[threading.Event] = None) -> bool:
        """
        将视频文件转换为MOV容器，保留视频流，音频转换为PCM 24bit格式
        对于采样率48000的视频，保持48000采样率不变
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            stop_event: 停止事件，用户取消时会被设置
            
        Returns:
            转换是否成功
        """
        logger.info("开始转换: input=%s output=%s", input_path, output_path)

        def report_error(message: str) -> None:
            logger.error(message)
            if error_callback:
                error_callback(message)
        
        try:
            if stop_event and stop_event.is_set():
                logger.info("检测到取消请求，跳过本次转换: %s", input_path)
                return False

            ffmpeg_path = find_ffmpeg_executable()
            if not ffmpeg_path:
                report_error("未找到 ffmpeg，无法执行转换。")
                return False

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                report_error(f"无法创建输出目录: {output_dir} ({exc})")
                return False
            logger.info("确保输出目录存在: %s", output_dir)
            
            # 获取文件信息，检查采样率
            file_info = FFmpegService.get_file_info(input_path)
            sample_rate = file_info.get('sample_rate') if file_info else None
            logger.info("检测到采样率: %s Hz", sample_rate)
            
            # 构建ffmpeg命令 - 保留视频流，只转换音频为PCM 24bit
            cmd = [
                ffmpeg_path,
                '-i', input_path,  # 输入文件
                '-c:v', 'copy',  # 视频流直接复制，不重新编码
                '-c:a', 'pcm_s24le',  # 音频转换为PCM 24bit little-endian
            ]
            
            # 对于采样率小于48000的视频，转换为48000；大于等于48000的保持原采样率
            if sample_rate is not None and sample_rate >= 48000:
                cmd.extend(['-ar', str(sample_rate)])  # 保持原采样率
                logger.info("保持原采样率 %s Hz", sample_rate)
            elif sample_rate is not None and sample_rate < 48000:
                cmd.extend(['-ar', '48000'])  # 转换为48000采样率
                logger.info("将采样率 %s Hz 转换为 48000 Hz", sample_rate)
            else:
                logger.warning("采样率信息获取失败，使用 ffmpeg 默认处理")
            
            cmd.extend([
                '-f', 'mov',  # MOV容器格式
                '-y',  # 覆盖输出文件
                output_path
            ])
            
            logger.info("执行命令: %s", " ".join(cmd))
            
            # 执行转换
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            logger.info("ffmpeg 进程ID: %s", process.pid)
            
            # 解析进度信息
            duration = None
            logger.info("开始解析 ffmpeg 输出")
            
            for line in process.stdout:
                if stop_event and stop_event.is_set():
                    logger.info("收到取消请求，尝试终止 ffmpeg 进程")
                    ConverterService._terminate_process(process)
                    ConverterService._remove_incomplete_output(output_path)
                    return False
                logger.info("[ffmpeg] %s", line.strip())
                
                if progress_callback:
                    # 尝试解析时长信息
                    if duration is None and "Duration:" in line:
                        try:
                            time_str = line.split("Duration:")[1].split(",")[0].strip()
                            h, m, s = time_str.split(':')
                            duration = float(h) * 3600 + float(m) * 60 + float(s)
                            logger.info("解析到时长: %s 秒", duration)
                        except Exception as e:
                            logger.warning("解析时长失败: %s", e)
                    
                    # 尝试解析当前时间
                    if duration is not None and "time=" in line:
                        try:
                            time_str = line.split("time=")[1].split(" ")[0].strip()
                            h, m, s = time_str.split(':')
                            current_time = float(h) * 3600 + float(m) * 60 + float(s)
                            progress = min(100.0, (current_time / duration) * 100)
                            logger.info("进度更新: %.1f%%", progress)
                            progress_callback(progress)
                        except Exception as e:
                            logger.warning("解析进度失败: %s", e)
            
            # 等待进程完成
            logger.info("等待 ffmpeg 进程完成")
            if stop_event and stop_event.is_set():
                logger.info("收到取消请求，终止等待")
                ConverterService._terminate_process(process)
                ConverterService._remove_incomplete_output(output_path)
                return False
            return_code = process.wait()
            logger.info("进程返回码: %s", return_code)
            
            if return_code == 0:
                # 检查输出文件是否存在
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info("转换成功，输出文件大小: %s 字节", file_size)
                else:
                    logger.warning("进程成功但输出文件不存在: %s", output_path)
                
                if progress_callback:
                    progress_callback(100.0)
                return True
            else:
                report_error(f"ffmpeg 转换失败，返回码: {return_code}")
                ConverterService._remove_incomplete_output(output_path)
                return False
        except FileNotFoundError:
            report_error("未找到 ffmpeg 可执行文件，无法启动转换。")
            ConverterService._remove_incomplete_output(output_path)
            return False
        except Exception as e:
            report_error(f"转换出错: {e}")
            import traceback
            logger.error("错误详情: %s", traceback.format_exc())
            ConverterService._remove_incomplete_output(output_path)
            return False
    
    @staticmethod
    def batch_convert(input_files: List[str], output_dir: str,
                     progress_callback: Optional[Callable[[ConversionProgress], None]] = None,
                     stop_event: Optional[threading.Event] = None,
                     max_workers: int = 2) -> List[bool]:
        """
        批量转换文件（多线程版本）
        
        Args:
            input_files: 输入文件路径列表
            output_dir: 输出目录
            progress_callback: 总进度回调函数
            stop_event: 停止事件
            max_workers: 最大并发线程数
            
        Returns:
            每个文件转换是否成功的结果列表
        """
        logger.info("开始批量转换: files=%s max_workers=%s output_dir=%s", len(input_files), max_workers, output_dir)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化进度信息
        progress_info = ConversionProgress()
        progress_info.total_files = len(input_files)
        progress_info.status = "准备中"
        
        if progress_callback:
            progress_callback(progress_info)
        
        # 创建结果列表，保持与输入文件的顺序一致
        results = [False] * len(input_files)
        per_file_errors = [""] * len(input_files)
        
        # 用于跟踪完成情况
        completed_count = 0
        completed_lock = threading.Lock()
        per_file_progress = [0.0] * len(input_files)
        active_files = set()
        progress_info.status = "转换中"
        progress_info.active_threads = min(max_workers, len(input_files))
        if progress_callback:
            progress_callback(progress_info.snapshot())

        def emit_progress() -> None:
            if not progress_callback:
                return

            progress_callback(progress_info.snapshot())

        def update_total_progress() -> None:
            if not input_files:
                progress_info.total_progress = 0.0
                return

            progress_info.total_progress = sum(per_file_progress) / len(input_files)

        def update_active_file_progresses() -> None:
            progress_info.active_file_progresses = [
                (os.path.basename(input_files[index]), per_file_progress[index])
                for index in sorted(active_files)
            ]
        
        def process_file(file_index: int, input_path: str) -> tuple[int, bool]:
            """处理单个文件的函数"""
            if stop_event and stop_event.is_set():
                print(f"[多线程转换] 检测到取消请求，跳过文件: {input_path}")
                return file_index, False
            
            logger.info("开始处理文件 %s/%s: %s", file_index + 1, len(input_files), input_path)
            
            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                logger.error("输入文件不存在: %s", input_path)
                with completed_lock:
                    per_file_errors[file_index] = "输入文件不存在。"
                return file_index, False

            with completed_lock:
                active_files.add(file_index)
                progress_info.current_file = os.path.basename(input_path)
                progress_info.current_progress = 0.0
                progress_info.active_threads = len(active_files)
                update_total_progress()
                update_active_file_progresses()
                emit_progress()
            
            # 生成输出文件名
            output_path = ConverterService.build_output_path(input_path, output_dir)
            logger.info("输出路径: %s", output_path)
            
            # 单文件进度回调（线程安全）
            def file_progress(p):
                with completed_lock:
                    per_file_progress[file_index] = p
                    progress_info.current_file = os.path.basename(input_path)
                    progress_info.current_progress = p
                    progress_info.active_threads = len(active_files)
                    update_total_progress()
                    update_active_file_progresses()
                    emit_progress()

            def file_error(message: str):
                with completed_lock:
                    per_file_errors[file_index] = message
            
            # 执行转换
            success = ConverterService.convert_to_pcm_mov(
                input_path,
                output_path,
                file_progress,
                file_error,
                stop_event
            )
            
            return file_index, success
        
        # 使用线程池执行转换
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(process_file, i, file_path): i 
                for i, file_path in enumerate(input_files)
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_index):
                if stop_event and stop_event.is_set():
                    logger.info("检测到取消请求，停止处理新任务")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                file_index, success = future.result()
                
                # 更新结果
                with completed_lock:
                    results[file_index] = success
                    completed_count += 1
                    
                    # 更新进度信息
                    progress_info.completed_files = completed_count
                    progress_info.current_file = os.path.basename(input_files[file_index])
                    progress_info.current_progress = 100.0 if success else 0.0
                    per_file_progress[file_index] = 100.0 if success else 0.0
                    active_files.discard(file_index)
                    progress_info.active_threads = len(active_files)
                    update_total_progress()
                    update_active_file_progresses()
                    
                    if success:
                        progress_info.status = "转换中"
                        progress_info.error_message = ""
                    else:
                        progress_info.status = "部分文件转换失败"
                        reason = per_file_errors[file_index] or "未知错误"
                        progress_info.error_message = f"{os.path.basename(input_files[file_index])}: {reason}"
                    
                    emit_progress()
                    
                    logger.info("文件 %s 处理完成，成功=%s", file_index + 1, success)
        
        # 检查是否被取消
        if stop_event and stop_event.is_set():
            progress_info.status = "已取消"
        else:
            success_count = sum(results)
            if success_count == len(results):
                progress_info.status = "全部完成"
            else:
                progress_info.status = "部分完成"
                failed_messages = [
                    f"{os.path.basename(input_files[i])}: {per_file_errors[i] or '未知错误'}"
                    for i, success in enumerate(results) if not success
                ]
                progress_info.error_message = "；".join(failed_messages[:2])
        
        progress_info.active_threads = 0
        update_total_progress()
        update_active_file_progresses()
        if progress_callback:
            progress_callback(progress_info.snapshot())
        
        logger.info("批量转换完成，结果: %s", results)
        return results
    
    @staticmethod
    def check_ffmpeg_available() -> bool:
        """检查本地ffmpeg是否可用"""
        try:
            ffmpeg_path = find_ffmpeg_executable()
            if not os.path.exists(ffmpeg_path):
                return False
            subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
            return True
        except (TypeError, FileNotFoundError, subprocess.CalledProcessError):
            return False
