"""
Excel文件读取工具
提供Excel文件的读取和保存功能
"""

import pandas as pd
import tkinter as tk
from tkinter import filedialog
import subprocess
import sys

def install_package(package):
    """自动安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError:
        print(f"无法自动安装{package}，请手动运行: pip install {package}")
        return False
    return True

# 检查并安装openpyxl
try:
    import openpyxl
except ImportError:
    print("检测到缺少openpyxl依赖，正在尝试自动安装...")
    if not install_package("openpyxl"):
        sys.exit(1)

def select_file(title: str) -> str:
    """弹出文件选择对话框"""
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title=title)

def read_excel_file():
    """
    读取Excel文件并保存副本
    通过GUI对话框选择输入/输出文件
    保留原始Excel文件中的所有sheet
    """
    # 选择输入文件
    input_file = select_file("选择要转换的Excel文件")
    if not input_file:
        print("未选择文件")
        return
    
    # 读取Excel文件中的所有sheet
    excel_file = pd.ExcelFile(input_file)
    sheet_names = excel_file.sheet_names
    
    # 创建字典保存所有sheet的数据
    sheets_data = {}
    for sheet in sheet_names:
        df = pd.read_excel(input_file, sheet_name=sheet)
        sheets_data[sheet] = df
    
    # 选择输出文件
    output_file = filedialog.asksaveasfilename(
        title="保存转换结果",
        defaultextension=".xlsx",
        filetypes=[("Excel文件", "*.xlsx")]
    )
    if not output_file:
        print("未选择输出文件")
        return
    
    # 使用ExcelWriter保存多个sheet
    with pd.ExcelWriter(output_file) as writer:
        for sheet_name, df in sheets_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"文件保存完成: {output_file}")

if __name__ == "__main__":
    read_excel_file()
