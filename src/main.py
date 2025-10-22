import os
import argparse
from typing import List, Tuple, Dict, Optional
from PIL import Image
import cv2
import subprocess
from media_integrity_checker import MediaIntegrityChecker


def main():
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
