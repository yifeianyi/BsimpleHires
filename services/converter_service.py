import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional

from .ffmpeg_service import FFmpegService
from .settings_service import SettingsService
from utils.logging_utils import get_logger
from utils.path_utils import find_ffmpeg_executable

logger = get_logger(__name__)


class ConversionProgress:
    def __init__(self):
        self.current_file = ""
        self.total_files = 0
        self.completed_files = 0
        self.current_progress = 0.0
        self.total_progress = 0.0
        self.status = "等待中"
        self.error_message = ""
        self.active_threads = 0
        self.active_file_progresses: list[tuple[str, float]] = []

    def snapshot(self) -> 'ConversionProgress':
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
    OUTPUT_SUFFIX = '_bsimple'

    @staticmethod
    def _hidden_process_kwargs() -> dict:
        kwargs = {}
        if os.name != 'nt':
            return kwargs

        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        if creationflags:
            kwargs['creationflags'] = creationflags

        startupinfo_factory = getattr(subprocess, 'STARTUPINFO', None)
        use_show_window = getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
        if startupinfo_factory and use_show_window:
            startupinfo = startupinfo_factory()
            startupinfo.dwFlags |= use_show_window
            kwargs['startupinfo'] = startupinfo

        return kwargs

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
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
                logger.info('已删除未完成输出: %s', output_path)
        except OSError as exc:
            logger.warning('删除未完成输出失败: %s - %s', output_path, exc)

    @staticmethod
    def build_output_path(input_path: str, output_dir: str) -> str:
        settings = SettingsService.load()
        input_name = Path(input_path).stem
        base_name = f'{input_name}{ConverterService.OUTPUT_SUFFIX}'
        candidate = Path(output_dir) / f'{base_name}.mov'

        if settings.naming_strategy == 'overwrite':
            return str(candidate)

        suffix = 2
        while candidate.exists():
            candidate = Path(output_dir) / f'{base_name}_{suffix}.mov'
            suffix += 1

        return str(candidate)

    @staticmethod
    def convert_to_pcm_mov(
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> bool:
        logger.info('开始转换: input=%s output=%s', input_path, output_path)

        def report_error(message: str) -> None:
            logger.error(message)
            if error_callback:
                error_callback(message)

        try:
            if stop_event and stop_event.is_set():
                logger.info('检测到取消请求，跳过本次转换: %s', input_path)
                return False

            ffmpeg_path = find_ffmpeg_executable()
            if not ffmpeg_path:
                report_error('未找到 ffmpeg，无法执行转换。')
                return False

            output_dir = os.path.dirname(output_path)
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                report_error(f'无法创建输出目录: {output_dir} ({exc})')
                return False

            file_info = FFmpegService.get_file_info(input_path)
            sample_rate = file_info.get('sample_rate') if file_info else None

            cmd = [
                ffmpeg_path,
                '-i', input_path,
                '-c:v', 'copy',
                '-c:a', 'pcm_s24le',
            ]

            if sample_rate is not None and sample_rate >= 48000:
                cmd.extend(['-ar', str(sample_rate)])
                logger.info('保持原采样率 %s Hz', sample_rate)
            elif sample_rate is not None and sample_rate < 48000:
                cmd.extend(['-ar', '48000'])
                logger.info('将采样率 %s Hz 转换为 48000 Hz', sample_rate)
            else:
                logger.warning('采样率信息获取失败，使用 ffmpeg 默认处理')

            cmd.extend(['-f', 'mov', '-y', output_path])
            logger.info('执行命令: %s', ' '.join(cmd))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                **ConverterService._hidden_process_kwargs(),
            )

            cancel_monitor_done = threading.Event()

            def monitor_cancellation() -> None:
                if not stop_event:
                    return
                stop_event.wait()
                if cancel_monitor_done.is_set():
                    return
                if process.poll() is None:
                    logger.info('收到取消请求，主动终止 ffmpeg 进程')
                    ConverterService._terminate_process(process)

            cancel_monitor = threading.Thread(
                target=monitor_cancellation,
                name='ffmpeg-cancel-monitor',
                daemon=True,
            )
            cancel_monitor.start()

            duration = None
            for line in process.stdout:
                logger.info('[ffmpeg] %s', line.strip())

                if not progress_callback:
                    continue

                if duration is None and 'Duration:' in line:
                    try:
                        time_str = line.split('Duration:')[1].split(',')[0].strip()
                        hours, minutes, seconds = time_str.split(':')
                        duration = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                    except Exception as exc:
                        logger.warning('解析时长失败: %s', exc)

                if duration is not None and 'time=' in line:
                    try:
                        time_str = line.split('time=')[1].split(' ')[0].strip()
                        hours, minutes, seconds = time_str.split(':')
                        current_time = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                        progress_callback(min(100.0, current_time / duration * 100))
                    except Exception as exc:
                        logger.warning('解析进度失败: %s', exc)

            return_code = process.wait()
            cancel_monitor_done.set()
            cancel_monitor.join(timeout=0.2)

            if stop_event and stop_event.is_set():
                ConverterService._remove_incomplete_output(output_path)
                return False

            if return_code == 0:
                if progress_callback:
                    progress_callback(100.0)
                return True

            report_error(f'ffmpeg 转换失败，返回码: {return_code}')
            ConverterService._remove_incomplete_output(output_path)
            return False
        except FileNotFoundError:
            report_error('未找到 ffmpeg 可执行文件，无法启动转换。')
            ConverterService._remove_incomplete_output(output_path)
            return False
        except Exception as exc:
            report_error(f'转换出错: {exc}')
            logger.exception('转换异常')
            ConverterService._remove_incomplete_output(output_path)
            return False

    @staticmethod
    def batch_convert(
        input_files: List[str],
        output_dir: str,
        progress_callback: Optional[Callable[[ConversionProgress], None]] = None,
        stop_event: Optional[threading.Event] = None,
        max_workers: int = 2,
    ) -> List[bool]:
        logger.info('开始批量转换: files=%s max_workers=%s output_dir=%s', len(input_files), max_workers, output_dir)
        os.makedirs(output_dir, exist_ok=True)

        progress_info = ConversionProgress()
        progress_info.total_files = len(input_files)
        progress_info.status = '准备中'
        if progress_callback:
            progress_callback(progress_info.snapshot())

        results = [False] * len(input_files)
        per_file_errors = [''] * len(input_files)
        completed_count = 0
        completed_lock = threading.Lock()
        per_file_progress = [0.0] * len(input_files)
        active_files: set[int] = set()

        progress_info.status = '转换中'
        progress_info.active_threads = min(max_workers, len(input_files))
        if progress_callback:
            progress_callback(progress_info.snapshot())

        def emit_progress() -> None:
            if progress_callback:
                progress_callback(progress_info.snapshot())

        def update_total_progress() -> None:
            progress_info.total_progress = sum(per_file_progress) / len(input_files) if input_files else 0.0

        def update_active_file_progresses() -> None:
            progress_info.active_file_progresses = [
                (os.path.basename(input_files[index]), per_file_progress[index])
                for index in sorted(active_files)
            ]

        def process_file(file_index: int, input_path: str) -> tuple[int, bool]:
            if stop_event and stop_event.is_set():
                logger.info('检测到取消请求，跳过文件: %s', input_path)
                return file_index, False

            if not os.path.exists(input_path):
                logger.error('输入文件不存在: %s', input_path)
                with completed_lock:
                    per_file_errors[file_index] = '输入文件不存在。'
                return file_index, False

            with completed_lock:
                active_files.add(file_index)
                progress_info.current_file = os.path.basename(input_path)
                progress_info.current_progress = 0.0
                progress_info.active_threads = len(active_files)
                update_total_progress()
                update_active_file_progresses()
                emit_progress()

            output_path = ConverterService.build_output_path(input_path, output_dir)
            logger.info('输出路径: %s', output_path)

            def file_progress(value: float) -> None:
                with completed_lock:
                    per_file_progress[file_index] = value
                    progress_info.current_file = os.path.basename(input_path)
                    progress_info.current_progress = value
                    progress_info.active_threads = len(active_files)
                    update_total_progress()
                    update_active_file_progresses()
                    emit_progress()

            def file_error(message: str) -> None:
                with completed_lock:
                    per_file_errors[file_index] = message

            success = ConverterService.convert_to_pcm_mov(
                input_path,
                output_path,
                file_progress,
                file_error,
                stop_event,
            )
            return file_index, success

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(process_file, index, file_path): index
                for index, file_path in enumerate(input_files)
            }

            for future in as_completed(future_to_index):
                try:
                    file_index, success = future.result()
                except Exception as exc:
                    logger.exception('批量转换任务异常')
                    file_index = future_to_index[future]
                    success = False
                    per_file_errors[file_index] = str(exc)

                with completed_lock:
                    results[file_index] = success
                    completed_count += 1
                    progress_info.completed_files = completed_count
                    progress_info.current_file = os.path.basename(input_files[file_index])
                    progress_info.current_progress = 100.0 if success else 0.0
                    per_file_progress[file_index] = 100.0 if success else 0.0
                    active_files.discard(file_index)
                    progress_info.active_threads = len(active_files)
                    update_total_progress()
                    update_active_file_progresses()

                    if success:
                        progress_info.status = '转换中'
                        progress_info.error_message = ''
                    else:
                        progress_info.status = '部分文件转换失败'
                        reason = per_file_errors[file_index] or '未知错误'
                        progress_info.error_message = f"{os.path.basename(input_files[file_index])}: {reason}"

                    emit_progress()

        if stop_event and stop_event.is_set():
            progress_info.status = '已取消'
        else:
            success_count = sum(results)
            if success_count == len(results):
                progress_info.status = '全部完成'
            else:
                progress_info.status = '部分完成'
                failed_messages = [
                    f"{os.path.basename(input_files[i])}: {per_file_errors[i] or '未知错误'}"
                    for i, success in enumerate(results)
                    if not success
                ]
                progress_info.error_message = '；'.join(failed_messages[:2])

        progress_info.active_threads = 0
        update_total_progress()
        update_active_file_progresses()
        if progress_callback:
            progress_callback(progress_info.snapshot())

        logger.info('批量转换完成，结果: %s', results)
        return results

    @staticmethod
    def check_ffmpeg_available() -> bool:
        try:
            ffmpeg_path = find_ffmpeg_executable()
            if not ffmpeg_path or not os.path.exists(ffmpeg_path):
                return False
            subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                check=True,
                **ConverterService._hidden_process_kwargs(),
            )
            return True
        except (TypeError, FileNotFoundError, subprocess.CalledProcessError):
            return False
