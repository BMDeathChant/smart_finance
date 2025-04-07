"""
表格数据爬取模块

提供TableScraper类用于从网页抓取表格数据并保存为结构化格式(CSV/Excel)

主要功能:
- 支持快速模式(requests+BeautifulSoup)和JS渲染模式(Selenium)
- 自动处理多级表头和单元格合并
- 智能表格数据对齐
- 支持多表格同时抓取
- 自动重试机制
- 完善的日志记录

示例用法:
    from table_scraper import TableScraper
    
    # 快速模式
    scraper = TableScraper(mode='fast')
    tables = scraper.scrape_table("https://example.com")
    scraper.save_to_excel(tables, "output/data")
    
    # JS模式(需要chromedriver)
    scraper = TableScraper(mode='js', driver_path="chromedriver.exe")
    tables = scraper.scrape_table("https://example.com")
    scraper.save_to_csv(tables, "output/data")
    
注意事项:
- JS模式需要安装Selenium和对应浏览器驱动
- 建议使用try-finally确保资源释放
"""

# HTTP请求库 - 用于发送网络请求
import requests
# HTML解析库 - 用于解析网页内容
from bs4 import BeautifulSoup
# 数据分析库 - 用于处理表格数据
import pandas as pd
# 日志记录库 - 用于记录程序运行日志
import logging
# 类型提示 - 用于类型注解
from typing import List, Dict, Optional, Literal, Union
# 操作系统接口 - 用于文件路径操作
import os
# 时间库 - 用于时间相关操作
import time
# 浏览器自动化库 - 用于处理需要JavaScript渲染的网页
from selenium import webdriver
# Chrome浏览器选项配置 - 用于设置无头模式等参数
from selenium.webdriver.chrome.options import Options
# 元素定位器 - 提供By.CSS_SELECTOR等定位方式
from selenium.webdriver.common.by import By
# 显式等待工具 - 用于等待特定元素加载完成
from selenium.webdriver.support.ui import WebDriverWait
# 预期条件 - 提供元素可见、可点击等判断条件
from selenium.webdriver.support import expected_conditions as EC

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TableScraper:
    def __init__(self, 
                 headers: Optional[Dict] = None,
                 mode: Literal['fast', 'js'] = 'fast',
                 driver_path: Optional[str] = None):
        """初始化爬虫
        
        Args:
            headers: 请求头字典
            mode: 爬取模式 ('fast'=快速模式, 'js'=JS渲染模式)
            driver_path: 浏览器驱动路径(仅JS模式需要)
        """
        self.mode = mode
        self.session = requests.Session()
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        if mode == 'js':
            from selenium.webdriver.chrome.service import Service
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(
                service=service,
                options=options
            )

    def scrape_table(self, 
                   url: str, 
                   table_attrs: Optional[Dict] = None,
                   table_index: Optional[int] = None,
                   max_retries: int = 3) -> List[pd.DataFrame]:
        """从指定URL抓取表格数据
        
        Args:
            url: 目标网页URL
            table_attrs: 表格属性字典，用于定位特定表格
            table_index: 表格索引(从0开始)，None表示返回所有表格
            max_retries: 最大重试次数(仅JS模式)
            
        Returns:
            包含表格数据的DataFrame列表
            
        Raises:
            ValueError: 当无法找到表格时
            requests.RequestException: 当请求失败时
        """
        try:
            logger.info(f"开始抓取URL: {url}")
            # 检查URL有效性
            if not url.startswith(('http://', 'https://')):
                raise ValueError("无效的URL格式，必须以http://或https://开头")
                
            if self.mode == 'fast':
                response = self.session.get(url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table', attrs=table_attrs) if table_attrs else soup.find_all('table')
            else:
                for attempt in range(max_retries):
                    try:
                        self.driver.get(url)
                        # 等待页面完全加载
                        WebDriverWait(self.driver, 15).until(
                            lambda d: d.execute_script('return document.readyState') == 'complete')
                        
                        # 智能等待表格出现
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'table')))
                            
                        # 滚动到表格位置确保完全渲染
                        table = self.driver.find_element(By.CSS_SELECTOR, 'table')
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", table)
                        
                        # 添加额外等待确保数据加载
                        time.sleep(1)
                        
                        html = self.driver.page_source
                        soup = BeautifulSoup(html, 'html.parser')
                        tables = soup.find_all('table', attrs=table_attrs) if table_attrs else soup.find_all('table')
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {str(e)}")
                        time.sleep(2)
            
            if not tables:
                raise ValueError("未找到表格元素")
                
            results = []
            for table in tables:
                # 解析表头 - 处理可能的多级表头
                headers = []
                header_rows = table.find_all('tr', class_=lambda x: x and 'header' in x.lower()) or [table.find('tr')]
                
                for row in header_rows:
                    for th in row.find_all(['th', 'td']):
                        colspan = int(th.get('colspan', 1))
                        if colspan > 1:
                            headers.extend([th.get_text(strip=True)] * colspan)
                        else:
                            headers.append(th.get_text(strip=True))
                
                # 解析表格内容 - 自动对齐列数
                data = []
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if cells and not any('header' in c.get('class', []) for c in cells):
                        row_data = []
                        for cell in cells:
                            colspan = int(cell.get('colspan', 1))
                            row_data.extend([cell.get_text(strip=True)] * colspan)
                        
                        # 自动对齐列数
                        if len(row_data) > len(headers):
                            row_data = row_data[:len(headers)]
                        elif len(row_data) < len(headers):
                            row_data.extend([''] * (len(headers) - len(row_data)))
                        
                        data.append(row_data)
                        
                # 创建DataFrame - 处理可能为空的情况
                if not headers:
                    headers = [f'Column_{i}' for i in range(1, len(data[0])+1)] if data else ['Data']
                
                df = pd.DataFrame(data, columns=headers[:len(data[0])] if data else pd.DataFrame(columns=headers))
                results.append(df)
                logger.info(f"成功抓取表格数据，共{len(df)}行")
            
            if table_index is not None:
                if table_index >= len(results):
                    raise ValueError(f"表格索引{table_index}超出范围(共{len(results)}个表格)")
                return [results[table_index]]
            return results
            
        except requests.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"解析表格时出错: {e}")
            raise
            
    def close(self):
        """关闭浏览器驱动(仅JS模式需要)"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def save_to_csv(self, 
                  df: Union[pd.DataFrame, List[pd.DataFrame]], 
                  filename: str,
                  table_index: Optional[int] = None) -> None:
        """保存数据到CSV文件
        
        Args:
            df: 要保存的DataFrame或DataFrame列表
            filename: 输出文件名(不带扩展名)
            table_index: 当df为列表时，指定保存哪个表格
        """
        try:
            if isinstance(df, list):
                if table_index is not None:
                    if table_index >= len(df):
                        raise ValueError(f"表格索引{table_index}超出范围(共{len(df)}个表格)")
                    df[table_index].to_csv(f"{filename}_{table_index}.csv", index=False, encoding='utf-8-sig')
                else:
                    for i, table_df in enumerate(df):
                        table_df.to_csv(f"{filename}_{i}.csv", index=False, encoding='utf-8-sig')
            else:
                df.to_csv(f"{filename}.csv", index=False, encoding='utf-8-sig')
            logger.info(f"数据已保存到 {filename}*.csv")
        except Exception as e:
            logger.error(f"保存文件时出错: {e}")
            raise

    def save_to_excel(self, 
                     df: Union[pd.DataFrame, List[pd.DataFrame]], 
                     filename: str,
                     sheet_names: Union[str, List[str]] = None) -> None:
        """保存数据到Excel文件
        
        Args:
            df: 要保存的DataFrame或DataFrame列表
            filename: 输出文件名(不带扩展名)
            sheet_names: 工作表名称或名称列表(默认为Table1, Table2...)
        """
        try:
            if isinstance(df, list):
                # 自动生成sheet名称
                if sheet_names is None:
                    sheet_names = [f"Table{i+1}" for i in range(len(df))]
                elif isinstance(sheet_names, str):
                    sheet_names = [f"{sheet_names}_{i+1}" for i in range(len(df))]
                elif len(sheet_names) != len(df):
                    # 自动补齐或截断sheet名称
                    if len(sheet_names) < len(df):
                        sheet_names.extend([f"Sheet{i+1}" for i in range(len(sheet_names), len(df))])
                    else:
                        sheet_names = sheet_names[:len(df)]
                
                with pd.ExcelWriter(f"{filename}.xlsx") as writer:
                    for i, table_df in enumerate(df):
                        table_df.to_excel(writer, index=False, sheet_name=sheet_names[i])
            else:
                sheet_name = sheet_names[0] if isinstance(sheet_names, list) else sheet_names or "Table1"
                df.to_excel(f"{filename}.xlsx", index=False, sheet_name=sheet_name)
            logger.info(f"数据已保存到 {filename}.xlsx")
        except Exception as e:
            logger.error(f"保存文件时出错: {e}")
            raise

# 模块导出
__all__ = ['TableScraper']

