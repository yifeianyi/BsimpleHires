import os
import threading
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from services.converter_service import ConversionProgress, ConverterService
from services.ffmpeg_service import FFmpegService
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class ConversionWorker(QObject):
    progress_updated = pyqtSignal(ConversionProgress)
    finished = pyqtSignal(list)
    cancelled = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, input_files: List[str], output_dir: str, max_workers: int = 2):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.max_workers = max_workers
        self._is_running = False
        self.stop_event = threading.Event()

    def run(self):
        logger.info('工作线程开始执行转换任务: files=%s output_dir=%s', len(self.input_files), self.output_dir)
        try:
            self._is_running = True
            if not ConverterService.check_ffmpeg_available():
                error_msg = FFmpegService.get_availability_error() or '未检测到 ffmpeg，无法进行转换。'
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            os.makedirs(self.output_dir, exist_ok=True)

            def progress_callback(progress_info: ConversionProgress):
                if self._is_running:
                    self.progress_updated.emit(progress_info)

            results = ConverterService.batch_convert(
                self.input_files,
                self.output_dir,
                progress_callback,
                stop_event=self.stop_event,
                max_workers=self.max_workers,
            )

            if self.stop_event.is_set():
                self.cancelled.emit(results)
            elif self._is_running:
                self.finished.emit(results)
        except Exception as exc:
            logger.exception('工作线程异常')
            if self._is_running:
                self.error.emit(f'转换过程中出现错误: {exc}')

    def stop(self):
        self.stop_event.set()


class ConversionThreadManager:
    def __init__(self):
        self.current_thread: Optional[QThread] = None
        self.current_worker: Optional[ConversionWorker] = None

    def start_conversion(
        self,
        input_files: List[str],
        output_dir: str,
        progress_callback=None,
        finished_callback=None,
        error_callback=None,
        max_workers: int = 2,
    ) -> bool:
        logger.info('请求启动转换任务: max_workers=%s output_dir=%s', max_workers, output_dir)
        if self.current_thread and self.current_thread.isRunning():
            logger.warning('已有任务在运行，拒绝启动新任务')
            return False

        self.current_thread = QThread()
        self.current_worker = ConversionWorker(input_files, output_dir, max_workers)
        self.current_worker.moveToThread(self.current_thread)

        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.finished.connect(self._on_finished)
        self.current_worker.cancelled.connect(self._on_finished)
        self.current_worker.error.connect(self._on_error)
        self.current_worker.progress_updated.connect(self._on_progress)

        if progress_callback:
            self.current_worker.progress_updated.connect(progress_callback)
        if finished_callback:
            self.current_worker.finished.connect(finished_callback)
            self.current_worker.cancelled.connect(finished_callback)
        if error_callback:
            self.current_worker.error.connect(error_callback)

        self.current_thread.start()
        return True

    def stop_conversion(self):
        if self.current_worker:
            self.current_worker.stop()

    def is_running(self) -> bool:
        return bool(self.current_thread and self.current_thread.isRunning())

    def _on_finished(self, results):
        self.current_thread.quit()
        self.current_thread.wait()
        self.current_thread = None
        self.current_worker = None

    def _on_error(self, error_msg):
        self.current_thread.quit()
        self.current_thread.wait()
        self.current_thread = None
        self.current_worker = None

    def _on_progress(self, progress_info):
        pass
