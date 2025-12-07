from PyQt6.QtCore import QObject, pyqtSignal, QThread
from typing import List, Optional
import os

from services.converter_service import ConverterService, ConversionProgress


class ConversionWorker(QObject):
    """转换工作线程"""
    
    # 信号定义
    progress_updated = pyqtSignal(ConversionProgress)  # 进度更新
    finished = pyqtSignal(list)  # 转换完成，传递结果列表
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, input_files: List[str], output_dir: str):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self._is_running = False
    
    def run(self):
        """执行转换任务"""
        print(f"[工作线程] 开始执行转换任务")
        print(f"[工作线程] 输入文件数量: {len(self.input_files)}")
        print(f"[工作线程] 输出目录: {self.output_dir}")
        
        try:
            self._is_running = True
            print(f"[工作线程] 线程状态设置为运行中")
            
            # 检查ffmpeg是否可用
            print(f"[工作线程] 检查ffmpeg可用性...")
            if not ConverterService.check_ffmpeg_available():
                error_msg = "未检测到ffmpeg，无法进行转换"
                print(f"[工作线程] 错误: {error_msg}")
                self.error.emit(error_msg)
                return
            
            print(f"[工作线程] ffmpeg检查通过")
            
            # 确保输出目录存在
            print(f"[工作线程] 创建输出目录...")
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"[工作线程] 输出目录已确保存在: {self.output_dir}")
            
            # 进度回调函数
            def progress_callback(progress_info: ConversionProgress):
                if self._is_running:
                    print(f"[工作线程] 进度更新: {progress_info.current_file} - {progress_info.current_progress:.1f}% - {progress_info.status}")
                    self.progress_updated.emit(progress_info)
            
            # 执行批量转换
            print(f"[工作线程] 开始执行批量转换...")
            results = ConverterService.batch_convert(
                self.input_files, 
                self.output_dir,
                progress_callback
            )
            
            print(f"[工作线程] 批量转换完成，结果: {results}")
            
            if self._is_running:
                print(f"[工作线程] 发送完成信号")
                self.finished.emit(results)
            else:
                print(f"[工作线程] 任务被取消，不发送完成信号")
                
        except Exception as e:
            error_msg = f"转换过程中出现错误: {str(e)}"
            print(f"[工作线程] 异常: {error_msg}")
            import traceback
            print(f"[工作线程] 异常详情: {traceback.format_exc()}")
            
            if self._is_running:
                self.error.emit(error_msg)
    
    def stop(self):
        """停止转换任务"""
        self._is_running = False


class ConversionThreadManager:
    """转换线程管理器"""
    
    def __init__(self):
        self.current_thread: Optional[QThread] = None
        self.current_worker: Optional[ConversionWorker] = None
    
    def start_conversion(self, input_files: List[str], output_dir: str,
                        progress_callback=None, finished_callback=None, 
                        error_callback=None) -> bool:
        """
        启动转换任务
        
        Args:
            input_files: 输入文件列表
            output_dir: 输出目录
            progress_callback: 进度回调函数
            finished_callback: 完成回调函数
            error_callback: 错误回调函数
            
        Returns:
            是否成功启动
        """
        print(f"[线程管理器] 请求启动转换任务")
        print(f"[线程管理器] 输入文件: {input_files}")
        print(f"[线程管理器] 输出目录: {output_dir}")
        
        # 如果已有任务在运行，先停止
        if self.current_thread and self.current_thread.isRunning():
            print(f"[线程管理器] 警告: 已有任务在运行，拒绝启动新任务")
            return False
        
        # 创建工作线程
        print(f"[线程管理器] 创建新的工作线程")
        self.current_thread = QThread()
        self.current_worker = ConversionWorker(input_files, output_dir)
        self.current_worker.moveToThread(self.current_thread)
        
        # 连接信号
        print(f"[线程管理器] 连接信号和槽")
        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.finished.connect(self._on_finished)
        self.current_worker.error.connect(self._on_error)
        self.current_worker.progress_updated.connect(self._on_progress)
        
        # 连接用户回调
        if progress_callback:
            self.current_worker.progress_updated.connect(progress_callback)
            print(f"[线程管理器] 已连接进度回调")
        if finished_callback:
            self.current_worker.finished.connect(finished_callback)
            print(f"[线程管理器] 已连接完成回调")
        if error_callback:
            self.current_worker.error.connect(error_callback)
            print(f"[线程管理器] 已连接错误回调")
        
        # 启动线程
        print(f"[线程管理器] 启动工作线程")
        self.current_thread.start()
        print(f"[线程管理器] 工作线程已启动")
        return True
    
    def stop_conversion(self):
        """停止当前转换任务"""
        if self.current_worker:
            self.current_worker.stop()
        if self.current_thread:
            self.current_thread.quit()
            self.current_thread.wait()
    
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