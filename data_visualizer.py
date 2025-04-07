"""
数据分析可视化模块
提供常用数据可视化功能，基于matplotlib和seaborn
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
from typing import Optional, Dict, Any, List
import logging

class DataVisualizer:
    def __init__(self):
        """初始化数据可视化器"""
        self.logger = logging.getLogger(__name__)
        set_style()  # 设置默认样式
    
    def plot_line(self, df: pd.DataFrame, x: str, y: str, 
                 title: str = '', xlabel: str = '', ylabel: str = '',
                 figsize: tuple = (10, 6), financial: bool = False, **kwargs) -> plt.Figure:
        """绘制折线图(类方法封装)"""
        self.logger.info(f"绘制折线图: {title}")
        return line_plot(df, x, y, title, xlabel, ylabel, figsize, financial, **kwargs)
    
    def plot_bar(self, df: pd.DataFrame, x: str, y: str, 
                title: str = '', xlabel: str = '', ylabel: str = '',
                figsize: tuple = (10, 6), financial: bool = False, **kwargs) -> plt.Figure:
        """绘制柱状图(类方法封装)"""
        self.logger.info(f"绘制柱状图: {title}")
        return bar_plot(df, x, y, title, xlabel, ylabel, figsize, financial, **kwargs)
    
    def plot_scatter(self, df: pd.DataFrame, x: str, y: str, 
                    hue: Optional[str] = None,
                    title: str = '', xlabel: str = '', ylabel: str = '',
                    figsize: tuple = (10, 6), **kwargs) -> plt.Figure:
        """绘制散点图(类方法封装)"""
        self.logger.info(f"绘制散点图: {title}")
        return scatter_plot(df, x, y, hue, title, xlabel, ylabel, figsize, **kwargs)
    
    def plot_correlation(self, df: pd.DataFrame, 
                       method: str = 'pearson',
                       figsize: tuple = (10, 8), 
                       annot: bool = True,
                       **kwargs) -> plt.Figure:
        """绘制相关系数矩阵(类方法封装)"""
        self.logger.info("绘制相关系数矩阵热力图")
        return plot_correlation_matrix(df, method, figsize, annot, **kwargs)

    def plot_hist(self, df: pd.DataFrame, x: str,
                bins: int = 10, kde: bool = True,
                title: str = '', xlabel: str = '', ylabel: str = 'Frequency',
                figsize: tuple = (10, 6), **kwargs) -> plt.Figure:
        """绘制直方图(类方法封装)"""
        self.logger.info(f"绘制直方图: {title}")
        return hist_plot(df, x, bins, kde, title, xlabel, ylabel, figsize, **kwargs)

    def save_plot(self, fig: plt.Figure, filename: str, 
                 dpi: int = 300, bbox_inches: str = 'tight') -> None:
        """保存图表
        
        Args:
            fig: matplotlib Figure对象
            filename: 保存文件名
            dpi: 图片分辨率
            bbox_inches: 边界框设置
        """
        fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches)
        plt.close(fig)

    def visualize(self, df: pd.DataFrame, save_path: str = "output/visualization.png"):
        """自动可视化DataFrame数据
        
        Args:
            df: 要可视化的DataFrame
            save_path: 图表保存路径
        """
        self.logger.info("开始数据可视化...")
        
        # 确保数据适合可视化
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) >= 2:
            # 两列以上数值数据 - 散点图
            fig = self.plot_scatter(df, numeric_cols[0], numeric_cols[1],
                                  title=f"{numeric_cols[0]} vs {numeric_cols[1]}")
        elif len(numeric_cols) == 1:
            # 单列数值数据 - 直方图
            fig = self.plot_hist(df, numeric_cols[0], 
                               title="数据分布", 
                               xlabel=numeric_cols[0])
        else:
            # 非数值数据 - 柱状图
            if len(df.columns) >= 2:
                fig = self.plot_bar(df, df.columns[0], df.columns[1])
            else:
                raise ValueError("没有足够的列进行可视化")
        
        # 保存图表
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        self.save_plot(fig, save_path)
        self.logger.info(f"可视化图表已保存到 {save_path}")

def set_style(style: str = 'whitegrid', context: str = 'notebook') -> None:
    """设置绘图样式
    
    Args:
        style: seaborn样式 ('whitegrid', 'darkgrid', 'white', 'dark', 'ticks')
        context: 绘图上下文 ('paper', 'notebook', 'talk', 'poster')
    """
    sns.set_style(style)
    sns.set_context(context)
    plt.rcParams['font.family'] = 'SimHei'  # 中文显示
    plt.rcParams['axes.unicode_minus'] = False  # 负号显示
    
def set_financial_style() -> None:
    """设置财务报表专用样式"""
    sns.set_style("whitegrid", {
        'grid.linestyle': '--',
        'grid.alpha': 0.3,
        'axes.edgecolor': '0.15',
        'axes.linewidth': 1.2
    })
    plt.rcParams['font.family'] = 'SimHei'
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['axes.titlesize'] = 14

def line_plot(df: pd.DataFrame, x: str, y: str, 
              title: str = '', xlabel: str = '', ylabel: str = '',
              figsize: tuple = (10, 6), financial: bool = False, **kwargs) -> plt.Figure:
    """绘制折线图
    
    Args:
        df: 输入DataFrame
        x: x轴列名
        y: y轴列名
        title: 图表标题
        xlabel: x轴标签
        ylabel: y轴标签
        figsize: 图表尺寸
        financial: 是否为财务图表
        **kwargs: 其他传递给sns.lineplot的参数
    
    Returns:
        matplotlib Figure对象
    """
    if financial:
        set_financial_style()
        kwargs.setdefault('color', '#2E86C1')  # 财务蓝色
    fig, ax = plt.subplots(figsize=figsize)
    sns.lineplot(data=df, x=x, y=y, ax=ax, **kwargs)
    ax.set_title(title, pad=20)
    ax.set_xlabel(xlabel, labelpad=10)
    ax.set_ylabel(ylabel, labelpad=10)
    
    if financial:
        ax.yaxis.grid(True, linestyle='--', alpha=0.6)
        ax.xaxis.grid(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
    return fig

def bar_plot(df: pd.DataFrame, x: str, y: str, 
             title: str = '', xlabel: str = '', ylabel: str = '',
             figsize: tuple = (10, 6), financial: bool = False, **kwargs) -> plt.Figure:
    """绘制柱状图
    
    Args:
        df: 输入DataFrame
        x: x轴列名
        y: y轴列名
        title: 图表标题
        xlabel: x轴标签
        ylabel: y轴标签
        figsize: 图表尺寸
        financial: 是否为财务图表
        **kwargs: 其他传递给sns.barplot的参数
    
    Returns:
        matplotlib Figure对象
    """
    if financial:
        set_financial_style()
        kwargs.setdefault('palette', ['#3498DB', '#2ECC71', '#E74C3C'])  # 财务配色
    fig, ax = plt.subplots(figsize=figsize)
    sns.barplot(data=df, x=x, y=y, ax=ax, **kwargs)
    ax.set_title(title, pad=20)
    ax.set_xlabel(xlabel, labelpad=10)
    ax.set_ylabel(ylabel, labelpad=10)
    
    if financial:
        for p in ax.patches:
            ax.annotate(f"{p.get_height():.2f}", 
                       (p.get_x() + p.get_width() / 2., p.get_height()),
                       ha='center', va='center', 
                       xytext=(0, 5), 
                       textcoords='offset points')
        ax.yaxis.grid(True, linestyle='--', alpha=0.6)
        ax.xaxis.grid(False)
        
    return fig

def scatter_plot(df: pd.DataFrame, x: str, y: str, 
                 hue: Optional[str] = None,
                 title: str = '', xlabel: str = '', ylabel: str = '',
                 figsize: tuple = (10, 6), **kwargs) -> plt.Figure:
    """绘制散点图
    
    Args:
        df: 输入DataFrame
        x: x轴列名
        y: y轴列名
        hue: 分组变量
        title: 图表标题
        xlabel: x轴标签
        ylabel: y轴标签
        figsize: 图表尺寸
        **kwargs: 其他传递给sns.scatterplot的参数
    
    Returns:
        matplotlib Figure对象
    """
    fig, ax = plt.subplots(figsize=figsize)
    sns.scatterplot(data=df, x=x, y=y, hue=hue, ax=ax, **kwargs)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig

def box_plot(df: pd.DataFrame, x: str, y: str, 
             title: str = '', xlabel: str = '', ylabel: str = '',
             figsize: tuple = (10, 6), **kwargs) -> plt.Figure:
    """绘制箱线图
    
    Args:
        df: 输入DataFrame
        x: x轴列名
        y: y轴列名
        title: 图表标题
        xlabel: x轴标签
        ylabel: y轴标签
        figsize: 图表尺寸
        **kwargs: 其他传递给sns.boxplot的参数
    
    Returns:
        matplotlib Figure对象
    """
    fig, ax = plt.subplots(figsize=figsize)
    sns.boxplot(data=df, x=x, y=y, ax=ax, **kwargs)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig

def hist_plot(df: pd.DataFrame, x: str, 
              bins: int = 10, kde: bool = True,
              title: str = '', xlabel: str = '', ylabel: str = 'Frequency',
              figsize: tuple = (10, 6), **kwargs) -> plt.Figure:
    """绘制直方图
    
    Args:
        df: 输入DataFrame
        x: 数据列名
        bins: 分箱数量
        kde: 是否显示核密度估计
        title: 图表标题
        xlabel: x轴标签
        ylabel: y轴标签
        figsize: 图表尺寸
        **kwargs: 其他传递给sns.histplot的参数
    
    Returns:
        matplotlib Figure对象
    """
    fig, ax = plt.subplots(figsize=figsize)
    sns.histplot(data=df, x=x, bins=bins, kde=kde, ax=ax, **kwargs)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig

def plot_correlation_matrix(df: pd.DataFrame, 
                           method: str = 'pearson',
                           figsize: tuple = (10, 8), 
                           annot: bool = True,
                           **kwargs) -> plt.Figure:
    """绘制相关系数矩阵热力图
    
    Args:
        df: 输入DataFrame
        method: 相关系数计算方法 ('pearson', 'kendall', 'spearman')
        figsize: 图表尺寸
        annot: 是否显示数值
        **kwargs: 其他传递给sns.heatmap的参数
    
    Returns:
        matplotlib Figure对象
    """
    corr = df.corr(method=method)
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(corr, annot=annot, ax=ax, **kwargs)
    return fig
