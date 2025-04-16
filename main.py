"""
数据爬取与分析主程序 - Flask Web版本
整合表格爬取、数据清洗、分析和可视化功能
"""

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from dash import html
from table_scraper import TableScraper
from data_cleaner import DataCleaner
from data_visualizer import DataVisualizer
from openai_wrapper import AIDataAssistant
from number_converter import NumberConverter
from data_cleaner import DataCleaner
from du_point_unit import create_app as create_du_point_app, run_app
import pandas as pd
import logging
import os
from dotenv import load_dotenv
from io import StringIO
import sys

# 配置日志
"""logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)"""


from io import StringIO
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
class LogCollector:
    def __init__(self):
        self.log_buffer = StringIO()
        #self.logger = logging.getLogger('smart_logger')
        #self.logger.setLevel(logging.INFO)
        self.handler = logging.StreamHandler(self.log_buffer)
        self.handler.setFormatter(logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S'))
        

        # 绑定到 root logger，确保所有日志都会进来
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self.handler)
        # 避免重复添加 handler
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            root_logger.addHandler(self.handler)

        # 每次程序启动时清空日志缓存
        self.log_buffer.truncate(0)
        self.log_buffer.seek(0)

    def get_logs(self):
        self.log_buffer.seek(0)
        logs = []
        for line in self.log_buffer.readlines():
            try:
                time_part, rest = line.split(' - ', 1)
                level, message = rest.split(' - ', 1)
                logs.append({
                    'time': time_part.strip(),
                    'level': level.strip(),
                    'message': message.strip()
                })
            except:
                continue
        return logs
    def get_logger(self):
        return logging.getLogger() 


# 创建Flask应用
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'output'

class MainApp:
    def __init__(self, log_collector):
        """初始化各功能模块"""
        self.scraper = TableScraper(mode='js', driver_path='chromedriver.exe')
        load_dotenv()
        self.ai_assistant = AIDataAssistant(api_key=os.getenv('OPENAI_API_KEY'))
        self.log_collector = log_collector
        self.logger = log_collector.get_logger()

    def run_pipeline(self, url: str):
        """运行数据处理流程直到转置完成"""
        try:
            # 1. 爬取表格数据并保存为Excel
            self.logger.info("开始爬取表格数据...")
            tables = self.scraper.scrape_table(url)
            if not tables:
                raise ValueError("未找到任何表格数据")
            
            excel_path = os.path.join("output", "financial_data.xlsx")
            try:
                os.makedirs("output", exist_ok=True, mode=0o777)
            except PermissionError:
                self.logger.error("无法创建output目录，请检查权限")
                raise
            with pd.ExcelWriter(excel_path) as writer:
                sheet_names = ["主要财务指标", "资产负债表", "利润表", "现金流量表"]
                for i, table in enumerate(tables):
                    name = sheet_names[i] if i < len(sheet_names) else f"Sheet{i+1}"
                    table.to_excel(writer, sheet_name=name, index=False)
            self.logger.info(f"表格数据已保存到: {excel_path}")

            # 2. 数据转置
            self.logger.info("开始数据转置...")
            with pd.ExcelFile(excel_path) as excel:
                sheets = {sheet: pd.read_excel(excel, sheet_name=sheet) for sheet in excel.sheet_names}
            
            for sheet_name, df in sheets.items():
                # 将第一列设为索引后再转置
                if len(df.columns) > 0:
                    df = df.set_index(df.columns[0])
                    sheets[sheet_name] = df.T
            
            with pd.ExcelWriter(excel_path) as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)  

            # 3. 数字转换并保存回原Excel
            self.logger.info("开始数字转换...")
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
                    df.to_excel(writer, sheet_name=sheet_name, index=False)  # 保持转置后的格式
            
            # 4. 数据清洗并保存回原Excel
            self.logger.info("开始数据清洗...")
            with pd.ExcelFile(excel_path) as excel:
                sheets = {sheet: pd.read_excel(excel, sheet_name=sheet) for sheet in excel.sheet_names}
            
            cleaner = DataCleaner()
            for sheet_name, df in sheets.items():
                sheets[sheet_name] = cleaner.clean_data(df)
            
            with pd.ExcelWriter(excel_path) as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)  # 保持转置后的格式
            
            self.logger.info("数据转置完成!")
            return {
                'status': 'transpose_completed',
                'excel_path': os.path.abspath(excel_path).replace("\\", "/")
            }


        except Exception as e:
            self.logger.error(f"流程执行出错: {e}")
            raise

    def continue_analysis(self, excel_path):
        """继续执行可视化分析和AI分析"""
        try:
            # 直接进行AI分析
            self.logger.info("开始AI分析...")
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
                        output_md="output/汇总分析_analysis.md"
                    )
            
            self.logger.info("所有流程完成!")
            return {}

        except Exception as e:
            self.logger.error(f"后续分析出错: {e}")
            raise

@app.route('/')
def index():
    return render_template('index.html')

from threading import Thread
from flask import jsonify, Response
import time


# 全局变量存储分析状态和结果
analysis_status = {}
analysis_results = {}

def background_analysis(url, task_id):
    try:
        #main_app = MainApp(LogCollector())
        initial_result = main_app.run_pipeline(url)
        
        if initial_result['status'] == 'transpose_completed':
            # 先返回转置完成状态
            analysis_results[task_id] = {
                'status': 'transpose_completed',
                'excel_path': initial_result['excel_path'],
                'error': None
            }
            
            # 继续执行后续分析
            main_app.continue_analysis(initial_result['excel_path'])
            analysis_results[task_id] = {
                'status': 'completed',
                'error': None
            }

    except Exception as e:
        analysis_results[task_id] = {
            'status': 'error',
            'error': str(e)
        }
@app.route('/logs')
def get_logs():
    logs = log_collector.get_logs()
    return jsonify(logs)

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url')
    if not url:
        url = "https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.html?code=03333&type=web&color=w#/newfinancialanalysis"
    
    task_id = str(time.time())
    analysis_status[task_id] = 'processing'
    
    # 启动后台线程处理分析任务
    thread = Thread(target=background_analysis, args=(url, task_id))
    thread.start()
    
    return jsonify({'task_id': task_id, 'status': 'processing'})

@app.route('/check_status/<task_id>')
def check_status(task_id):
    if task_id in analysis_results:
        result = analysis_results[task_id]
        if result['status'] == 'completed':
            return jsonify({
                'status': 'completed',
                'redirect': f'/results?task_id={task_id}'
            })
        elif result['status'] == 'transpose_completed':
            return jsonify({
                'status': 'transpose_completed',
                'redirect': f'/results?task_id={task_id}'
            })
        else:
            return jsonify({
                'status': 'error',
                'error': result['error']
            })
    elif task_id in analysis_status:
        return jsonify({'status': 'processing'})
    else:
        return jsonify({'status': 'not_found'}), 404

@app.route('/results')
def show_results():
    task_id = request.args.get('task_id')
    if not task_id or task_id not in analysis_results:
        return redirect(url_for('index'))

    result = analysis_results[task_id]
    logs = log_collector.get_logs()

    if result['status'] in ['completed', 'transpose_completed']:
        excel_path = result.get('excel_path')

        # 读取Excel表格为HTML
        excel_tables = {}
        try:
            xls = pd.ExcelFile(excel_path)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                html_table = df.to_html(classes='table table-bordered table-striped', index=True)
                excel_tables[sheet] = html_table
        except Exception as e:
            return render_template('results.html',
                                    error=f"Excel读取失败: {e}",
                                    excel_path=excel_path,
                                    excel_tables={},
                                    visualizations={},
                                    logs=logs
                               )

        return render_template('results.html',
                               excel_path=excel_path,
                               excel_tables=excel_tables,
                               visualizations={},
                               error=None,
                               logs=logs
                               )
    else:
        return render_template('results.html',
                               error=result.get('error'),
                               excel_path=None,
                               excel_tables={},
                               visualizations={},
                               logs=logs
                               )



@app.route('/download/<file_type>')
def download(file_type):
    if file_type == 'excel':
        filename = 'financial_data.xlsx'
    elif file_type == 'analysis':
        filename = 'combined_analysis.md'
    else:
        return "无效的文件类型", 404
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )

@app.route('/static/<filename>')
def static_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/du_point_analysis')
def du_point_analysis():
    excel_path = request.args.get('excel_path')
    if not excel_path:
        return redirect(url_for('index'))

    
    excel_path = os.path.abspath(excel_path).replace("\\", "/")
    print(f"📂 du_point_analysis 收到 Excel 路径: {excel_path}")

    try:
        from du_point_unit import create_app as create_du_point_app, run_app
        du_point_app, _, _ = create_du_point_app(excel_path=excel_path)
        
        # 确保应用已正确初始化
        if du_point_app.layout is None:
            du_point_app.layout = html.Div("杜邦分析加载中...")

        from threading import Thread
        thread = Thread(target=run_app, args=(du_point_app,))
        thread.daemon = True  # 设置为守护线程
        thread.start()

        return f"""
        <html>
            <head><meta charset="utf-8"><title>杜邦分析启动中</title></head>
            <body>
                <p>杜邦分析已启动，请点击打开：</p>
                <a href="http://127.0.0.1:8050/" target="_blank">http://127.0.0.1:8050/</a>
                <p>如果页面没有自动打开，请稍等几秒后手动点击链接</p>
            </body>
        </html>
        """
    except Exception as e:
        self.logger.error(f"杜邦分析启动失败: {e}")
        return render_template('results.html',
                               error=f"杜邦分析启动失败: {e}",
                               excel_path=excel_path)
log_collector = LogCollector()
logger = log_collector.get_logger()
main_app = MainApp(log_collector)


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=False)
