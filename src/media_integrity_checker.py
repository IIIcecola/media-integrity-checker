import os
import argparse
from typing import List, Tuple, Dict, Optional
from PIL import Image
import cv2
import subprocess

class MediaIntegrityChecker:
    """媒体文件完整性检测工具类"""
    
    # 支持的媒体格式
    SUPPORTED_IMAGES = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')
    SUPPORTED_VIDEOS = ('.mp4', '.avi', '.mkv', '.mov', '.flv')
    
    def __init__(self, directory: str = ".", recursive: bool = False, report_file: Optional[str] = None):
        """
        初始化检测工具
        :param directory: 检测目标目录
        :param recursive: 是否递归检测子目录
        :param report_file: 报告保存路径（可选）
        """
        self.directory = os.path.abspath(directory)
        self.recursive = recursive
        self.report_file = report_file
        self.media_files: List[str] = []
        self.results: List[Dict] = []
        self.total_count = 0
        self.ok_count = 0
        self.error_count = 0
        
        # 验证目录有效性
        if not os.path.isdir(self.directory):
            raise ValueError(f"目录 '{self.directory}' 不存在或不是有效目录")
    
    def scan_media_files(self) -> None:
        """扫描目录中的媒体文件"""
        self.media_files = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in self.SUPPORTED_IMAGES or file_ext in self.SUPPORTED_VIDEOS:
                    self.media_files.append(os.path.join(root, file))
            if not self.recursive:
                break  # 非递归模式只扫描当前目录
        
        self.total_count = len(self.media_files)
    
    def check_image_integrity(self, file_path: str) -> Tuple[bool, str]:
        """
        检测图片文件完整性
        :param file_path: 图片文件路径
        :return: (是否正常, 检测信息)
        """
        try:
            # 尝试打开图片并验证基本属性
            with Image.open(file_path) as img:
                # 验证图片尺寸（排除无效图片）
                if img.width <= 0 or img.height <= 0:
                    return False, f"无效图片尺寸: {img.width}x{img.height}"
                
                # 尝试读取图片数据（检测损坏数据）
                img.load()
                
                # 验证图片格式一致性
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext == '.jpg' and img.format != 'JPEG':
                    return False, f"格式不匹配: 文件后缀为{file_ext}，实际格式为{img.format}"
                if file_ext == '.png' and img.format != 'PNG':
                    return False, f"格式不匹配: 文件后缀为{file_ext}，实际格式为{img.format}"
            
            return True, "图片正常"
        
        except FileNotFoundError:
            return False, "文件不存在"
        except PermissionError:
            return False, "权限不足，无法读取文件"
        except Exception as e:
            return False, f"损坏或不支持的图片格式: {str(e)[:100]}"
    
    def check_video_integrity(self, file_path: str) -> Tuple[bool, str]:
        """
        检测视频文件完整性
        :param file_path: 视频文件路径
        :return: (是否正常, 检测信息)
        """
        duration = 0.0
        # 先通过ffprobe检测视频元数据（需要安装ffmpeg）
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True, text=True, check=True
            )
            duration = float(result.stdout.strip())
            if duration <= 0:
                return False, f"无效视频时长: {duration}秒"
        except FileNotFoundError:
            # 若无ffprobe，使用OpenCV进行基础检测
            pass
        except Exception as e:
            return False, f"ffprobe检测失败: {str(e)[:80]}"
        
        # 使用OpenCV检测视频帧完整性
        cap = None
        try:
            cap = cv2.VideoCapture(file_path)
            
            # 检查是否成功打开视频
            if not cap.isOpened():
                return False, "无法打开视频文件，可能已损坏"
            
            # 验证视频基本属性
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if frame_count <= 0:
                return False, f"无效帧数: {frame_count}"
            if fps <= 0:
                return False, f"无效帧率: {fps}"
            if width <= 0 or height <= 0:
                return False, f"无效视频尺寸: {width}x{height}"
            
            # 检测关键帧（读取前5帧和最后5帧，避免完整读取大文件）
            test_frames = [0, min(100, frame_count//2), max(0, frame_count-5)]
            for frame_idx in test_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    return False, f"帧{frame_idx}读取失败，视频可能损坏"
            
            return True, f"视频正常 (时长: {duration:.1f}秒, 分辨率: {width}x{height}, 帧数: {frame_count})"
        
        except FileNotFoundError:
            return False, "文件不存在"
        except PermissionError:
            return False, "权限不足，无法读取文件"
        except Exception as e:
            return False, f"损坏或不支持的视频格式: {str(e)[:100]}"
        finally:
            if cap is not None:
                cap.release()
    
    def run_checks(self) -> None:
        """执行所有媒体文件的完整性检测"""
        if not self.media_files:
            self.scan_media_files()
        
        if not self.media_files:
            return
        
        self.results = []
        self.ok_count = 0
        
        for idx, file_path in enumerate(self.media_files, 1):
            relative_path = os.path.relpath(file_path, self.directory)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            print(f"[{idx}/{self.total_count}] 检测: {relative_path}")
            
            if file_ext in self.SUPPORTED_IMAGES:
                is_ok, message = self.check_image_integrity(file_path)
                file_type = "IMAGE"
            else:
                is_ok, message = self.check_video_integrity(file_path)
                file_type = "VIDEO"
            
            # 输出结果
            status = "✅ 正常" if is_ok else "❌ 损坏"
            print(f"     状态: {status} - {message}\n")
            
            self.results.append({
                "path": relative_path,
                "type": file_type,
                "status": status,
                "message": message
            })
            
            if is_ok:
                self.ok_count += 1
        
        self.error_count = self.total_count - self.ok_count
    
    def generate_report(self) -> List[str]:
        """生成检测报告"""
        report = [
            "=" * 80,
            "媒体文件完整性检测报告",
            "=" * 80,
            f"检测目录: {self.directory}",
            f"扫描模式: {'递归扫描' if self.recursive else '当前目录'}",
            f"检测总数: {self.total_count} 个",
            f"正常文件: {self.ok_count} 个",
            f"损坏文件: {self.error_count} 个",
            "\n详细结果:",
            "-" * 80,
            f"{'文件路径':<50} {'类型':<8} {'状态':<10} {'说明'}",
            "-" * 80
        ]
        
        for res in self.results:
            # 处理长路径显示
            display_path = res["path"] if len(res["path"]) <= 50 else "..." + res["path"][-47:]
            report.append(f"{display_path:<50} {res['type']:<8} {res['status']:<10} {res['message']}")
        
        return report
    
    def save_report(self, report: List[str]) -> None:
        """保存报告到文件"""
        if self.report_file:
            with open(self.report_file, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
            print(f"\n完整报告已保存到: {os.path.abspath(self.report_file)}")
    
    def run(self) -> None:
        """运行完整检测流程"""
        print(f"正在扫描目录: {self.directory} {'(递归模式)' if self.recursive else ''}")
        self.scan_media_files()
        
        if not self.media_files:
            print("未发现支持的媒体文件")
            return
        
        print(f"发现 {self.total_count} 个媒体文件，开始检测...\n")
        self.run_checks()
        
        # 生成并显示报告
        report = self.generate_report()
        print("\n" + "\n".join(report[:8]))  # 显示汇总信息
        
        if self.report_file:
            self.save_report(report)
        else:
            print("\n".join(report[8:]))  # 显示详细结果


def main():
    # 检查依赖库
    try:
        from PIL import Image
    except ImportError:
        print("错误：未安装Pillow库，请先执行: pip install pillow")
        exit(1)
    
    try:
        import cv2
    except ImportError:
        print("错误：未安装OpenCV库，请先执行: pip install opencv-python")
        exit(1)
    
    # 命令行参数配置
    parser = argparse.ArgumentParser(description="媒体文件完整性检测工具")
    parser.add_argument("--dir", default=".", help="检测目标目录（默认当前目录）")
    parser.add_argument("--recursive", action="store_true", help="递归检测子目录")
    parser.add_argument("--report", help="将检测结果保存到指定文件（可选）")
    args = parser.parse_args()
    
    try:
        # 创建并运行检测工具
        checker = MediaIntegrityChecker(
            directory=args.dir,
            recursive=args.recursive,
            report_file=args.report
        )
        checker.run()
    except ValueError as e:
        print(f"错误：{e}")
        exit(1)


if __name__ == "__main__":
    main()
