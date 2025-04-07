"""
数据爬取与分析主程序
整合表格爬取、数据清洗、分析和可视化功能
"""

from table_scraper import TableScraper
from data_cleaner import DataCleaner
from data_visualizer import DataVisualizer
from openai_wrapper import AIDataAssistant
from number_converter import NumberConverter
from data_cleaner import DataCleaner
import pandas as pd
import logging
import os
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MainApp:
    def __init__(self):
        """初始化各功能模块"""
        self.scraper = TableScraper(mode='js', driver_path='chromedriver.exe')
        load_dotenv()
        self.ai_assistant = AIDataAssistant(api_key=os.getenv('OPENAI_API_KEY'))

    def run_pipeline(self, url: str):
        """运行完整数据处理流程"""
        try:
            # 1. 爬取表格数据并保存为Excel
            logger.info("开始爬取表格数据...")
            tables = self.scraper.scrape_table(url)
            if not tables:
                raise ValueError("未找到任何表格数据")
            
            excel_path = "output/financial_data.xlsx"
            os.makedirs("output", exist_ok=True)
            with pd.ExcelWriter(excel_path) as writer:
                sheet_names = ["主要财务指标", "资产负债表", "利润表", "现金流量表"]
                for i, table in enumerate(tables):
                    name = sheet_names[i] if i < len(sheet_names) else f"Sheet{i+1}"
                    table.to_excel(writer, sheet_name=name, index=False)
            logger.info(f"表格数据已保存到: {excel_path}")

            # 2. 数字转换并保存回原Excel
            logger.info("开始数字转换...")
            with pd.ExcelFile(excel_path) as excel:
                sheets = {sheet: pd.read_excel(excel, sheet_name=sheet) for sheet in excel.sheet_names}
            
            converter = NumberConverter()
            for sheet_name, df in sheets.items():
                for col in df.columns:
                    try:
                        df = converter.convert_column(df, col)
                    except Exception as e:
                        logger.warning(f"跳过表 {sheet_name} 的列 {col}: {str(e)}")
                sheets[sheet_name] = df
            
            with pd.ExcelWriter(excel_path) as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 3. 数据清洗并保存回原Excel
            logger.info("开始数据清洗...")
            with pd.ExcelFile(excel_path) as excel:
                sheets = {sheet: pd.read_excel(excel, sheet_name=sheet) for sheet in excel.sheet_names}
            
            cleaner = DataCleaner()
            for sheet_name, df in sheets.items():
                sheets[sheet_name] = cleaner.clean_data(df)
            
            with pd.ExcelWriter(excel_path) as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 4. 数据转置
            logger.info("开始数据转置...")
            with pd.ExcelFile(excel_path) as excel:
                sheets = {sheet: pd.read_excel(excel, sheet_name=sheet) for sheet in excel.sheet_names}
            
            for sheet_name, df in sheets.items():
                # 将第一列设为索引后再转置
                if len(df.columns) > 0:
                    df = df.set_index(df.columns[0])
                    sheets[sheet_name] = df.T
            
            with pd.ExcelWriter(excel_path) as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=True)  # 保留索引作为列名
            
            # 5. 数据可视化
            logger.info("生成数据可视化...")
            with pd.ExcelFile(excel_path) as excel:
                for sheet_name in excel.sheet_names:
                    df = pd.read_excel(excel, sheet_name=sheet_name)
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) >= 2:
                        DataVisualizer().visualize(
                            df[numeric_cols], 
                            f"output/financial_analysis_{sheet_name}.png"
                        )
                    else:
                        logger.warning(f"表 {sheet_name} 没有足够的数值列进行可视化")
            
            # 5. AI分析
            logger.info("开始AI分析...")
            with pd.ExcelFile(excel_path) as excel:
                # 单sheet分析
                for sheet_name in excel.sheet_names:
                    df = pd.read_excel(excel, sheet_name=sheet_name)
                    
                    # 根据sheet名称选择分析类型
                    if "Sheet1" in sheet_name or "主要财务指标" in sheet_name:
                        task = "financial_metrics"
                    elif "资产负债表" in sheet_name:
                        task = "balance_sheet"
                    elif "利润表" in sheet_name:
                        task = "income_statement"
                    elif "现金流量表" in sheet_name:
                        task = "cash_flow"
                    else:
                        task = "standard"
                    
                    result = self.ai_assistant.analyzer.analyze(
                        df, 
                        task=task,
                        output_md=f"output/{sheet_name}_analysis.md"
                    )
                
                # 合并sheet2-sheet4分析
                if len(excel.sheet_names) >= 4:
                    combined_data = {}
                    for sheet_name in excel.sheet_names[1:4]:  # sheet2-sheet4
                        df = pd.read_excel(excel, sheet_name=sheet_name)
                        combined_data[sheet_name] = df
                    
                    result = self.ai_assistant.analyzer.analyze_combined(
                        combined_data,
                        output_md="output/combined_analysis.md"
                    )
            
            logger.info("所有流程完成!")

        except Exception as e:
            logger.error(f"流程执行出错: {e}")
            raise

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import simpledialog
    
    def get_url():
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 创建输入对话框
        url = simpledialog.askstring(
            "输入财务数据URL",
            "请输入要分析的财务数据URL:\n示例: https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.html?code=03333&type=web&color=w#/newfinancialanalysis",
            initialvalue="https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.html?code=03333&type=web&color=w#/newfinancialanalysis"
        )
        
        if not url:
            print("使用默认示例URL")
            url = "https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.html?code=03333&type=web&color=w#/newfinancialanalysis"
        
        return url
    
    app = MainApp()
    url = get_url()
    app.run_pipeline(url)
