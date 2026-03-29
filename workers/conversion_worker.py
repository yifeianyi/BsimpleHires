from PyQt6.QtCore import QObject, pyqtSignal, QThread
from typing import List, Optional
import os
import threading

from services.ffmpeg_service import FFmpegService
from services.converter_service import ConverterService, ConversionProgress
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class ConversionWorker(QObject):
    """转换工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(ConversionProgress)  # 进度更新
    finished = pyqtSignal(list)  # 转换完成，传递结果列表
    cancelled = pyqtSignal(list)  # 转换取消，传递当前结果列表
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, input_files: List[str], output_dir: str, max_workers: int = 2):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.max_workers = max_workers
        self._is_running = False
        self.stop_event = threading.Event()
    
    def run(self):
        """执行转换任务"""
        logger.info("工作线程开始执行转换任务: files=%s output_dir=%s", len(self.input_files), self.output_dir)
        
        try:
            self._is_running = True
            logger.info("线程状态设置为运行中")
            
            # 检查ffmpeg是否可用
            logger.info("检查 ffmpeg 可用性")
            if not ConverterService.check_ffmpeg_available():
                error_msg = FFmpegService.get_availability_error() or "未检测到 ffmpeg，无法进行转换。"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return
            
            logger.info("ffmpeg 检查通过")
            
            # 确保输出目录存在
            logger.info("创建输出目录")
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info("输出目录已确保存在: %s", self.output_dir)
            
            # 进度回调函数
            def progress_callback(progress_info: ConversionProgress):
                if self._is_running:
                    logger.info("进度更新: %s - %.1f%% - %s", progress_info.current_file, progress_info.current_progress, progress_info.status)
                    self.progress_updated.emit(progress_info)
            
            # 执行批量转换
            logger.info("开始执行多线程批量转换，最大并发数: %s", self.max_workers)
            results = ConverterService.batch_convert(
                self.input_files, 
                self.output_dir,
                progress_callback,
                stop_event=self.stop_event,
                max_workers=self.max_workers
            )
            
            logger.info("批量转换完成，结果: %s", results)
            
            if self.stop_event.is_set():
                logger.info("发送取消信号")
                self.cancelled.emit(results)
            elif self._is_running:
                logger.info("发送完成信号")
                self.finished.emit(results)
            else:
                logger.info("任务被取消，不发送完成信号")
                
        except Exception as e:
            error_msg = f"转换过程中出现错误: {str(e)}"
            logger.error("工作线程异常: %s", error_msg)
            import traceback
            logger.error("异常详情: %s", traceback.format_exc())
            
            if self._is_running:
                self.error.emit(error_msg)
    
    def stop(self):
        """停止转换任务"""
        self.stop_event.set()


class ConversionThreadManager:
    """转换线程管理器"""
    
    def __init__(self):
        self.current_thread: Optional[QThread] = None
        self.current_worker: Optional[ConversionWorker] = None
    
    def start_conversion(self, input_files: List[str], output_dir: str,
                        progress_callback=None, finished_callback=None, 
                        error_callback=None, max_workers: int = 2) -> bool:
        """
        启动转换任务
        
        Args:
            input_files: 输入文件列表
            output_dir: 输出目录
            progress_callback: 进度回调函数
            finished_callback: 完成回调函数
            error_callback: 错误回调函数
            max_workers: 最大并发线程数
            
        Returns:
            是否成功启动
        """
        logger.info("请求启动多线程转换任务，最大并发数=%s，输出目录=%s", max_workers, output_dir)
        
        # 如果已有任务在运行，先停止
        if self.current_thread and self.current_thread.isRunning():
            logger.warning("已有任务在运行，拒绝启动新任务")
            return False
        
        # 创建工作线程
        logger.info("创建新的工作线程")
        self.current_thread = QThread()
        self.current_worker = ConversionWorker(input_files, output_dir, max_workers)
        self.current_worker.moveToThread(self.current_thread)
        
        # 连接信号
        logger.info("连接信号和槽")
        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.finished.connect(self._on_finished)
        self.current_worker.cancelled.connect(self._on_finished)
        self.current_worker.error.connect(self._on_error)
        self.current_worker.progress_updated.connect(self._on_progress)
        
        # 连接用户回调
        if progress_callback:
            self.current_worker.progress_updated.connect(progress_callback)
            logger.info("已连接进度回调")
        if finished_callback:
            self.current_worker.finished.connect(finished_callback)
            self.current_worker.cancelled.connect(finished_callback)
            logger.info("已连接完成回调")
        if error_callback:
            self.current_worker.error.connect(error_callback)
            logger.info("已连接错误回调")
        
        # 启动线程
        logger.info("启动工作线程")
        self.current_thread.start()
        logger.info("工作线程已启动")
        return True
    
    def stop_conversion(self):
        """停止当前转换任务"""
        if self.current_worker:
            self.current_worker.stop()
    
    def is_running(self) -> bool:
        """检查是否有任务在运行"""
        return self.current_thread and self.current_thread.isRunning()
    
    def _on_finished(self, results):
        """转换完成处理"""
        self.current_thread.quit()
        self.current_thread.wait()
        self.current_thread = None
        self.current_worker = None
    
    def _on_error(self, error_msg):
        """错误处理"""
        self.current_thread.quit()
        self.current_thread.wait()
        self.current_thread = None
        self.current_worker = None
    
    def _on_progress(self, progress_info):
        """进度更新处理"""
        pass  # 主要通过信号传递给用户回调
