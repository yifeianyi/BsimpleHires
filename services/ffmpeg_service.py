import subprocess
import json
import os
import sys
from typing import Optional, Dict, Any


class FFmpegService:
    """使用ffmpeg读取视频/音频文件信息的服务类"""
    
    @staticmethod
    def _get_ffmpeg_path():
        """获取本地ffmpeg路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller临时目录
                base_dir = sys._MEIPASS
            else:
                # 直接运行exe文件
                base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'ffmpeg')
    
    @staticmethod
    def get_file_info(filepath: str) -> Optional[Dict[str, Any]]:
        """
        使用ffprobe获取文件信息
        
        Args:
            filepath: 文件路径
            
        Returns:
            包含文件信息的字典，如果出错返回None
        """
        if not os.path.exists(filepath):
            return None
            
        try:
            # 使用ffprobe获取文件信息
            ffprobe_path = os.path.join(FFmpegService._get_ffmpeg_path(), 'ffprobe.exe')
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                filepath
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                print(f"ffprobe错误: {result.stderr}")
                return None
                
            data = json.loads(result.stdout)
            return FFmpegService._parse_file_info(data)
            
        except FileNotFoundError:
            print("错误: 未找到ffprobe，请确保已安装ffmpeg")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"获取文件信息时出错: {e}")
            return None
    
    @staticmethod
    def _parse_file_info(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析ffprobe返回的JSON数据
        
        Args:
            data: ffprobe返回的JSON数据
            
        Returns:
            解析后的文件信息字典
        """
        info = {
            'duration': None,
            'size': None,
            'audio_format': None,
            'video_format': None,
            'bit_rate': None,  # 音频码率
            'sample_rate': None,
            'channels': None,
            'resolution': None,
            'fps': None
        }
        
        # 从format中获取基本信息
        format_info = data.get('format', {})
        info['duration'] = float(format_info.get('duration', 0)) if format_info.get('duration') else None
        info['size'] = int(format_info.get('size', 0)) if format_info.get('size') else None
        
        # 从streams中获取详细信息
        streams = data.get('streams', [])
        for stream in streams:
            codec_type = stream.get('codec_type')
            
            if codec_type == 'audio':
                info['audio_format'] = stream.get('codec_name')
                info['sample_rate'] = int(stream.get('sample_rate', 0)) if stream.get('sample_rate') else None
                info['channels'] = int(stream.get('channels', 0)) if stream.get('channels') else None
                # 获取音频码率
                audio_bit_rate = stream.get('bit_rate')
                if audio_bit_rate:
                    info['bit_rate'] = int(audio_bit_rate)
                
            elif codec_type == 'video':
                info['video_format'] = stream.get('codec_name')
                width = stream.get('width')
                height = stream.get('height')
                if width and height:
                    info['resolution'] = f"{width}x{height}"
                
                # 获取帧率
                r_frame_rate = stream.get('r_frame_rate', '')
                if '/' in r_frame_rate:
                    try:
                        num, den = r_frame_rate.split('/')
                        fps = float(num) / float(den) if float(den) != 0 else None
                        info['fps'] = round(fps, 2) if fps else None
                    except (ValueError, ZeroDivisionError):
                        info['fps'] = None
        
        return info
    
    @staticmethod
    def check_ffmpeg_available() -> bool:
        """检查本地ffmpeg/ffprobe是否可用"""
        try:
            ffprobe_path = os.path.join(FFmpegService._get_ffmpeg_path(), 'ffprobe.exe')
            if not os.path.exists(ffprobe_path):
                return False
            subprocess.run([ffprobe_path, '-version'], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False