import subprocess
import os
import threading
from typing import Callable, Optional, List
from pathlib import Path


class ConversionProgress:
    """转换进度信息类"""
    def __init__(self):
        self.current_file = ""
        self.total_files = 0
        self.completed_files = 0
        self.current_progress = 0.0  # 当前文件进度 0-100
        self.status = "等待中"  # 等待中/转换中/已完成/出错
        self.error_message = ""


class ConverterService:
    """视频转音频服务类，将视频转换为MOV容器下的PCM 24bit音频格式"""
    
    @staticmethod
    def convert_to_pcm_mov(input_path: str, output_path: str, 
                          progress_callback: Optional[Callable[[float], None]] = None,
                          stop_event: Optional[threading.Event] = None) -> bool:
        """
        将视频文件转换为MOV容器，保留视频流，音频转换为PCM 24bit格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            stop_event: 停止事件，用户取消时会被设置
            
        Returns:
            转换是否成功
        """
        print(f"[转换服务] 开始转换: {input_path}")
        print(f"[转换服务] 输出路径: {output_path}")
        print(f"[转换服务] 转换模式: 保留视频流，音频转换为PCM 24bit")
        
        try:
            if stop_event and stop_event.is_set():
                print("[转换服务] 检测到取消请求，跳过本次转换")
                return False
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            print(f"[转换服务] 确保输出目录存在: {output_dir}")
            
            # 构建ffmpeg命令 - 保留视频流，只转换音频为PCM 24bit
            cmd = [
                'ffmpeg',
                '-i', input_path,  # 输入文件
                '-c:v', 'copy',  # 视频流直接复制，不重新编码
                '-c:a', 'pcm_s24le',  # 音频转换为PCM 24bit little-endian
                '-f', 'mov',  # MOV容器格式
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            print(f"[转换服务] 执行命令: {' '.join(cmd)}")
            
            # 执行转换
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            print(f"[转换服务] 进程ID: {process.pid}")
            
            # 解析进度信息
            duration = None
            print("[转换服务] 开始解析ffmpeg输出...")
            
            for line in process.stdout:
                if stop_event and stop_event.is_set():
                    print("[转换服务] 收到取消请求，尝试终止ffmpeg进程")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    return False
                print(f"[ffmpeg输出] {line.strip()}")
                
                if progress_callback:
                    # 尝试解析时长信息
                    if duration is None and "Duration:" in line:
                        try:
                            time_str = line.split("Duration:")[1].split(",")[0].strip()
                            h, m, s = time_str.split(':')
                            duration = float(h) * 3600 + float(m) * 60 + float(s)
                            print(f"[转换服务] 解析到时长: {duration}秒")
                        except Exception as e:
                            print(f"[转换服务] 解析时长失败: {e}")
                    
                    # 尝试解析当前时间
                    if duration is not None and "time=" in line:
                        try:
                            time_str = line.split("time=")[1].split(" ")[0].strip()
                            h, m, s = time_str.split(':')
                            current_time = float(h) * 3600 + float(m) * 60 + float(s)
                            progress = min(100.0, (current_time / duration) * 100)
                            print(f"[转换服务] 进度更新: {progress:.1f}%")
                            progress_callback(progress)
                        except Exception as e:
                            print(f"[转换服务] 解析进度失败: {e}")
            
            # 等待进程完成
            print("[转换服务] 等待进程完成...")
            if stop_event and stop_event.is_set():
                print("[转换服务] 收到取消请求，终止等待")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return False
            return_code = process.wait()
            print(f"[转换服务] 进程返回码: {return_code}")
            
            if return_code == 0:
                # 检查输出文件是否存在
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"[转换服务] 转换成功！输出文件大小: {file_size} 字节")
                else:
                    print(f"[转换服务] 警告: 进程成功但输出文件不存在: {output_path}")
                
                if progress_callback:
                    progress_callback(100.0)
                return True
            else:
                print(f"[转换服务] 转换失败，返回码: {return_code}")
                return False
                
        except Exception as e:
            print(f"[转换服务] 转换出错: {e}")
            import traceback
            print(f"[转换服务] 错误详情: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def batch_convert(input_files: List[str], output_dir: str,
                     progress_callback: Optional[Callable[[ConversionProgress], None]] = None,
                     stop_event: Optional[threading.Event] = None) -> List[bool]:
        """
        批量转换文件
        
        Args:
            input_files: 输入文件路径列表
            output_dir: 输出目录
            progress_callback: 总进度回调函数
            
        Returns:
            每个文件转换是否成功的结果列表
        """
        print(f"[批量转换] 开始批量转换，共 {len(input_files)} 个文件")
        print(f"[批量转换] 输出目录: {output_dir}")
        
        results = []
        progress_info = ConversionProgress()
        progress_info.total_files = len(input_files)
        
        if progress_callback:
            progress_callback(progress_info)
        
        for i, input_path in enumerate(input_files):
            if stop_event and stop_event.is_set():
                print("[批量转换] 检测到取消请求，提前结束")
                progress_info.status = "已取消"
                if progress_callback:
                    progress_callback(progress_info)
                break
            print(f"[批量转换] 处理第 {i+1}/{len(input_files)} 个文件: {input_path}")
            
            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                print(f"[批量转换] 错误: 输入文件不存在: {input_path}")
                results.append(False)
                continue
            
            # 更新进度信息
            progress_info.current_file = os.path.basename(input_path)
            progress_info.current_progress = 0.0
            progress_info.status = "转换中"
            progress_info.error_message = ""
            
            if progress_callback:
                progress_callback(progress_info)
            
            # 生成输出文件名
            input_name = Path(input_path).stem
            output_path = os.path.join(output_dir, f"{input_name}.mov")
            print(f"[批量转换] 输出路径: {output_path}")
            
            # 单文件进度回调
            def file_progress(p):
                progress_info.current_progress = p
                if progress_callback:
                    progress_callback(progress_info)
            
            # 执行转换
            success = ConverterService.convert_to_pcm_mov(
                input_path, output_path, file_progress
            )
            
            if success:
                progress_info.status = "已完成"
                print(f"[批量转换] 文件转换成功: {input_path}")
            else:
                progress_info.status = "出错"
                progress_info.error_message = f"转换失败: {input_path}"
                print(f"[批量转换] 文件转换失败: {input_path}")
            
            results.append(success)
            
            # 更新已完成文件数量和完成状态
            progress_info.completed_files = i + 1  # 当前文件已处理完成
            if progress_callback:
                progress_callback(progress_info)
        
        # 全部完成
        progress_info.status = "全部完成"
        progress_info.current_progress = 100.0
        success_count = sum(results)
        print(f"[批量转换] 批量转换完成！成功: {success_count}/{len(results)}")
        
        if progress_callback:
            progress_callback(progress_info)
        
        return results
    
    @staticmethod
    def check_ffmpeg_available() -> bool:
        """检查系统中是否安装了ffmpeg"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
