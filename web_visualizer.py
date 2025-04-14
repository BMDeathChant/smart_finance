"""
杜邦分析可视化模块
专注于财务杜邦分析可视化
"""
from pyecharts import options as opts
from pyecharts.charts import Tree
from typing import Dict
import pandas as pd
import logging
import json
import os
from tkinter import Tk, filedialog

class WebVisualizer:
    def __init__(self):
        """初始化可视化器"""
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def test_visualization():
        """测试杜邦分析可视化功能
        
        弹出文件选择对话框让用户选择财务数据文件
        """
        from pyecharts.charts import Page
        from pyecharts.globals import CurrentConfig
        CurrentConfig.ONLINE_HOST = "https://assets.pyecharts.org/assets/v5/"
        
        # 初始化可视化器
        visualizer = WebVisualizer()
        
        try:
            # 创建文件选择对话框
            root = Tk()
            root.withdraw()  # 隐藏主窗口
            file_path = filedialog.askopenfilename(
                title="选择财务数据文件",
                filetypes=[("Excel文件", "*.xlsx *.xls"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                print("未选择文件")
                return
                
            print(f"已选择文件: {file_path}")
            
            # 根据文件类型读取数据
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # 检查数据是否为空
            if df.empty:
                print("错误: 文件没有数据")
                return
                
            # 执行杜邦分析
            chart_config = visualizer.visualize_to_json(df)
            
            # 创建可视化页面
            page = Page()
            tree = (
                Tree(init_opts=opts.InitOpts(**chart_config.get("init_opts", {})))
                .add(
                    "",
                    chart_config["series"][0]["data"],
                    orient=chart_config["series"][0].get("orient", "TB"),
                    symbol=chart_config["series"][0].get("symbol", "roundRect"),
                    symbol_size=chart_config["series"][0].get("symbol_size", 12),
                    initial_tree_depth=chart_config["series"][0].get("initial_tree_depth", 2),
                    label_opts=opts.LabelOpts(
                        position=chart_config["series"][0].get("label_opts", {}).get("position", "top"),
                        vertical_align=chart_config["series"][0].get("label_opts", {}).get("vertical_align", "middle"),
                        font_size=chart_config["series"][0].get("label_opts", {}).get("font_size", 14)
                    )
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(**chart_config.get("title", {"title": "杜邦分析"})),
                    tooltip_opts=opts.TooltipOpts(**chart_config.get("tooltip", {"formatter": "{b}: {c}"}))
                )
            )
            page.add(tree)
            
            # 保存结果
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, "du_pont_analysis.html")
            page.render(output_file)
            print(f"杜邦分析结果已保存到: {output_file}")
            
            # 在浏览器中打开
            import webbrowser
            webbrowser.open(output_file)
            
        except Exception as e:
            print(f"处理文件时出错: {str(e)}")
    
    def visualize_to_json(self, df: pd.DataFrame) -> Dict:
        """执行杜邦分析并返回可视化配置
        
        Args:
            df: 包含财务指标的DataFrame
            必须包含列: 净利润、营业收入、总资产、股东权益
            
        Returns:
            包含杜邦分析图表配置的字典
        """
        self.logger.info("开始杜邦分析可视化...")
        return self._du_pont_analysis(df)

    def _du_pont_analysis(self, df: pd.DataFrame) -> Dict:
        """创建杜邦分析树状图
        
        Args:
            df: 包含财务指标的DataFrame
            必须包含以下列(支持多种名称):
            - 净利润/Net Profit/Net_Profit
            - 营业收入/Revenue/Operating_Income
            - 总资产/Total Assets/Total_Assets
            - 股东权益/Shareholders' Equity/Equity
            
        Returns:
            杜邦分析图表配置字典
        """
        # 优先查找预计算的指标列
        precomputed_cols = {
            "net_profit_margin": ["净利率(%)", "Net Profit Margin(%)"],
            "asset_turnover": ["总资产周转率(次)", "Asset Turnover(times)"],
            "equity_multiplier": ["权益乘数", "Equity Multiplier"]
        }
        
        # 检查是否有预计算指标
        use_precomputed = all(
            any(col in df.columns for col in cols)
            for cols in precomputed_cols.values()
        )
        
        if use_precomputed:
            # 使用预计算指标
            net_margin_col = next(col for col in precomputed_cols["net_profit_margin"] if col in df.columns)
            turnover_col = next(col for col in precomputed_cols["asset_turnover"] if col in df.columns)
            multiplier_col = next(col for col in precomputed_cols["equity_multiplier"] if col in df.columns)
            
            net_profit_margin = df[net_margin_col] 
            asset_turnover = df[turnover_col]
            equity_multiplier = df[multiplier_col]
        else:
            # 查找原始数据列进行计算
            col_mapping = {
                "net_profit": [
                    "净利润", 
                    "归母净利润(元)", 
                    "税后净利润", 
                    "本公司股东应占利润", 
                    "持续经营净利润", 
                    "净收益", 
                    "Net Profit", 
                    "Net_Profit", 
                    "Net Income", 
                    "Profit attributable to owners"
                ],
                "revenue": [
                    "营业收入", 
                    "营业总收入", 
                    "主营业务收入", 
                    "总收入", 
                    "营收", 
                    "销售收入", 
                    "商品销售收入", 
                    "营业总收入(元)", 
                    "Revenue", 
                    "Operating Revenue", 
                    "Operating_Income", 
                    "Sales"
                ],
                "total_assets": [
                    "总资产", 
                    "资产合计", 
                    "资产总计", 
                    "合计资产", 
                    "总计资产", 
                    "Total Assets", 
                    "Total_Assets", 
                    "资产总额"
                ],
                "equity": [
                    "股东权益", 
                    "本公司股东应占资本及储备", 
                    "归属于母公司股东权益", 
                    "所有者权益", 
                    "资本及储备", 
                    "净资产", 
                    "Shareholders' Equity", 
                    "Equity", 
                    "Owners' Equity", 
                    "Equity attributable to owners"
                ]
            }
            
            actual_cols = {}
            for key, possible_names in col_mapping.items():
                for name in possible_names:
                    if name in df.columns:
                        actual_cols[key] = name
                        break
                else:
                    raise ValueError(f"缺少必要列: 需要以下列之一: {possible_names}")

            # 计算杜邦分析指标
            net_profit_margin = df[actual_cols["net_profit"]] / df[actual_cols["revenue"]]  # 净利润率
            asset_turnover = df[actual_cols["revenue"]] / df[actual_cols["total_assets"]]  # 资产周转率
            equity_multiplier = df[actual_cols["total_assets"]] / df[actual_cols["equity"]]  # 权益乘数
        roe = net_profit_margin * asset_turnover * equity_multiplier  # ROE

        # 构建树状图数据
        data = [
            {
                "name": f"ROE: {roe.iloc[-1]:.2%}",
                "children": [
                    {
                        "name": f"净利润率: {net_profit_margin.iloc[-1]:.2%}",
                        "value": net_profit_margin.iloc[-1]
                    },
                    {
                        "name": f"资产周转率: {asset_turnover.iloc[-1]:.2f}",
                        "value": asset_turnover.iloc[-1]
                    },
                    {
                        "name": f"权益乘数: {equity_multiplier.iloc[-1]:.2f}",
                        "value": equity_multiplier.iloc[-1]
                    }
                ]
            }
        ]

        # 创建树状图
        tree = (
            Tree()
            .add(
                "",
                data,
                orient="TB",
                symbol="roundRect",
                symbol_size=12,
                initial_tree_depth=2,
                label_opts=opts.LabelOpts(
                    position="top",
                    vertical_align="middle",
                    font_size=14
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="杜邦分析"),
                tooltip_opts=opts.TooltipOpts(
                    formatter="{b}: {c}"
                )
            )
        )
        config = json.loads(tree.dump_options())
        # 确保title和tooltip是正确格式
        if "title" in config:
            if isinstance(config["title"], list):
                config["title"] = {"title": "杜邦分析"}
            elif not isinstance(config["title"], dict):
                config["title"] = {"title": str(config["title"])}
        else:
            config["title"] = {"title": "杜邦分析"}
            
        if "tooltip" in config:
            # 移除无效的show参数
            if isinstance(config["tooltip"], dict) and "show" in config["tooltip"]:
                del config["tooltip"]["show"]
            # 确保formatter存在
            if "formatter" not in config.get("tooltip", {}):
                config["tooltip"] = {"formatter": "{b}: {c}"}
        else:
            config["tooltip"] = {"formatter": "{b}: {c}"}
            
        return config

if __name__ == "__main__":
    WebVisualizer.test_visualization()
