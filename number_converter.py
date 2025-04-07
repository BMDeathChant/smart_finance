"""
中文数字转换模块
提供将中文数字字符串转换为阿拉伯数字的功能
支持单位: 万亿(1000000000000), 千亿(100000000000), 百亿(10000000000), 十亿(1000000000), 
亿(100000000), 千万(10000000), 百万(1000000), 十万(100000), 
万(10000), 千(1000), 百(100), 十(10)
"""

import pandas as pd
from typing import Union, Dict, Any

class NumberConverter:
    """中文数字转换器类"""
    
    UNITS = {
        '万亿': 1000000000000,
        '千亿': 100000000000,
        '百亿': 10000000000,
        '十亿': 1000000000,
        '亿': 100000000,
        '千万': 10000000,
        '百万': 1000000, 
        '十万': 100000,
        '万': 10000, 
        '千': 1000,
        '百': 100,
        '十': 10
    }
    
    @classmethod
    def convert_number(cls, cn_str: Union[str, float, int]) -> Union[int, float, Any]:
        """
        将中文数字字符串转换为阿拉伯数字
        
        Args:
            cn_str: 包含中文数字单位的字符串或数字，如"5万元"
        
        Returns:
            转换后的阿拉伯数字或原始值(如果是NaN或纯数字)
            
        Examples:
            >>> NumberConverter.convert_number("5万元")
            50000
            >>> NumberConverter.convert_number("3.5亿")
            350000000
            >>> NumberConverter.convert_number(50000)
            50000
            >>> NumberConverter.convert_number(3.5)
            3.5
            >>> NumberConverter.convert_number(float('nan'))
            nan
        """
        # 处理NaN值
        if isinstance(cn_str, float) and pd.isna(cn_str):
            return cn_str
            
        # 如果是数字类型且不包含单位，保持原样
        if isinstance(cn_str, (float, int)):
            return cn_str
            
        # 处理字符串类型
        cn_str = str(cn_str)
        for unit, multiplier in cls.UNITS.items():
            if unit in cn_str:
                try:
                    # 处理带单位的数字
                    num_str = cn_str.split(unit)[0].strip()
                    num = float(num_str)
                    return num * multiplier
                except ValueError:
                    
                    return cn_str  # 转换失败时返回原值
        return cn_str  # 如果没有单位，保持原样

    @classmethod
    def convert_column(cls, df: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        转换DataFrame指定列中的中文数字
        
        Args:
            df: 包含中文数字列的DataFrame
            column_name: 需要转换的列名
        
        Returns:
            转换后的DataFrame
        """
        # 只转换包含中文数字单位的列或纯数字
        col_str = df[column_name].astype(str)
        
        # 检查是否包含中文数字单位或符合数字格式
        def is_convertible(s):
            if pd.isna(s):
                return False
            try:
                float(str(s))
                return True
            except ValueError:
                return any(unit in str(s) for unit in cls.UNITS)
        
        if col_str.apply(is_convertible).any():
            df[column_name] = df[column_name].apply(
                lambda x: cls.convert_number(x) if is_convertible(str(x)) else x
            )
        return df

    