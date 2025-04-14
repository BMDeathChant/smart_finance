"""
数据清洗模块
提供数据清洗相关功能，包括处理缺失值、转换类型、去重、处理异常值等
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Union, Optional
import logging

class DataCleaner:
    def __init__(self):
        """初始化数据清洗器"""
        self.logger = logging.getLogger(__name__)
    
    def clean_data(self, df: pd.DataFrame, steps: Optional[Dict[str, Dict[str, Any]]] = None) -> pd.DataFrame:
        """执行数据清洗流程
        
        Args:
            df: 输入DataFrame
            steps: 清洗步骤配置字典 (可选)
                   (如 {'handle_missing': {'strategy': 'mean'}, 
                       'convert_types': {'type_map': {'date': 'datetime'}}})
        
        Returns:
            清洗后的DataFrame
        """
        self.logger.info("开始数据清洗...")
        if steps:
            return clean_data_pipeline(df, steps)
        else:
            # 默认清洗流程
            df = handle_missing_values(df)
            df = remove_duplicates(df)
            return df

def handle_missing_values(df: pd.DataFrame, strategy: str = 'mean', 
                         fill_value: Any = None) -> pd.DataFrame:
    """处理缺失值
    
    Args:
        df: 输入DataFrame
        strategy: 处理策略 ('mean', 'median', 'mode', 'drop', 'fill')
        fill_value: 当strategy='fill'时使用的填充值
    
    Returns:
        处理后的DataFrame
    """
    df = df.copy()
    # 将"--"替换为0
    df = df.replace('--', 0)
    df = df.replace(r"(\d{2})-(\d{2})-(\d{2})", r"\1/\2/\3", regex=True)
    if strategy == 'drop':
        df = df.dropna()
    elif strategy == 'fill':
        df = df.fillna(fill_value)
    else:
        for col in df.select_dtypes(include=[np.number]).columns:
            if strategy == 'mean':
                df[col].fillna(df[col].mean(), inplace=True)
            elif strategy == 'median':
                df[col].fillna(df[col].median(), inplace=True)
            elif strategy == 'mode':
                df[col].fillna(df[col].mode()[0], inplace=True)
    return df

def convert_types(df: pd.DataFrame, type_map: Dict[str, str]) -> pd.DataFrame:
    """转换数据类型
    
    Args:
        df: 输入DataFrame
        type_map: 列名到类型的映射字典 (如 {'age': 'int', 'date': 'datetime'})
    
    Returns:
        转换后的DataFrame
    """
    df = df.copy()
    for col, dtype in type_map.items():
        if dtype == 'datetime':
            df[col] = pd.to_datetime(df[col])
        elif dtype == 'category':
            df[col] = df[col].astype('category')
        else:
            df[col] = df[col].astype(dtype)
    return df

def remove_duplicates(df: pd.DataFrame, subset: Optional[list] = None, 
                      keep: str = 'first') -> pd.DataFrame:
    """移除重复行
    
    Args:
        df: 输入DataFrame
        subset: 用于判断重复的列列表
        keep: 保留哪个重复项 ('first', 'last', False)
    
    Returns:
        去重后的DataFrame
    """
    return df.drop_duplicates(subset=subset, keep=keep)

def handle_outliers(df: pd.DataFrame, method: str = 'clip', 
                   threshold: float = 3) -> pd.DataFrame:
    """处理异常值
    
    Args:
        df: 输入DataFrame
        method: 处理方法 ('clip', 'remove')
        threshold: 用于识别异常值的标准差倍数
    
    Returns:
        处理后的DataFrame
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        z_scores = (df[col] - df[col].mean()) / df[col].std()
        if method == 'clip':
            upper = df[col].mean() + threshold * df[col].std()
            lower = df[col].mean() - threshold * df[col].std()
            df[col] = df[col].clip(lower, upper)
        elif method == 'remove':
            df = df[(z_scores.abs() < threshold)]
    return df

def normalize_data(df: pd.DataFrame, method: str = 'minmax') -> pd.DataFrame:
    """数据标准化
    
    Args:
        df: 输入DataFrame
        method: 标准化方法 ('minmax', 'zscore')
    
    Returns:
        标准化后的DataFrame
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if method == 'minmax':
            col_min = df[col].min()
            col_max = df[col].max()
            if col_max != col_min:  # 避免除以0
                df[col] = (df[col] - col_min) / (col_max - col_min)
        elif method == 'zscore':
            col_mean = df[col].mean()
            col_std = df[col].std()
            if col_std != 0:  # 避免除以0
                df[col] = (df[col] - col_mean) / col_std
    return df

def save_to_excel(df: pd.DataFrame, file_path: str) -> None:
    """保存数据到Excel文件
    
    Args:
        df: 要保存的DataFrame
        file_path: 保存路径
    """
    df.to_excel(file_path, index=False)

def clean_data_pipeline(df: pd.DataFrame, 
                       steps: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """数据清洗管道
    
    Args:
        df: 输入DataFrame
        steps: 清洗步骤配置字典
               (如 {'handle_missing': {'strategy': 'mean'}, 
                   'convert_types': {'type_map': {'date': 'datetime'}}})
    
    Returns:
        清洗后的DataFrame
    """
    for step, params in steps.items():
        if step == 'handle_missing':
            df = handle_missing_values(df, **params)
        elif step == 'convert_types':
            df = convert_types(df, **params)
        elif step == 'remove_duplicates':
            df = remove_duplicates(df, **params)
        elif step == 'handle_outliers':
            df = handle_outliers(df, **params)
        elif step == 'normalize_data':
            df = normalize_data(df, **params)
    return df
