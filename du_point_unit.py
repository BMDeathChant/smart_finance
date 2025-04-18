import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import base64
import io
import json
from pyecharts.charts import Tree
from pyecharts import options as opts
from pyecharts.globals import CurrentConfig
import os
import zhconv

CurrentConfig.ONLINE_HOST = "https://assets.pyecharts.org/assets/v5/"

def create_app(excel_path=None):
    import dash
    from dash import dcc, html, Input, Output
    import pandas as pd
    import os

    app = dash.Dash(__name__)
    app.title = "杜邦分析（树图展示）"

    global cached_df, cached_years, source_logs, data_loaded
    data_loaded = False
    cached_df = None
    cached_years = []
    source_logs = {}

    if excel_path and os.path.exists(excel_path):
        print(f"📂 加载 Excel 路径: {excel_path}")
        try:
            xls = pd.ExcelFile(excel_path)
            print(f"📊 Excel 包含工作表: {xls.sheet_names}")
            
            # 首先尝试从"主要财务指标"表读取预计算字段
            if "主要财务指标" in xls.sheet_names:
                df = xls.parse("主要财务指标")
                df.columns = [normalize_column(col) for col in df.columns]
                if all(col in df.columns for col in PRECOMPUTED_COLUMNS.values()):
                    df["截止日期"] = pd.to_datetime(df["截止日期"], format="%y/%m/%d", errors='coerce')
                    df = df[df["截止日期"].dt.year >= 2000]
                    df["年份"] = df["截止日期"].dt.year.astype(str)
                    df.set_index("年份", inplace=True)

                    df["净利润率"] = df[PRECOMPUTED_COLUMNS["net_profit_margin"]] / 100
                    df["资产周转率"] = df[PRECOMPUTED_COLUMNS["asset_turnover"]]
                    df["权益乘数"] = df[PRECOMPUTED_COLUMNS["equity_multiplier"]]
                    df["总资产收益率"] = df[PRECOMPUTED_COLUMNS["return_on_total_assets"]]

                    cached_df = df
                    cached_years = df.index.unique().tolist()
                    source_logs = {k: "主要财务指标表直接读取" for k in PRECOMPUTED_COLUMNS}
                    """return app, cached_df, cached_years"""

            # 回退计算路径：遍历所有 Sheet 查找字段
            dfs = {name: xls.parse(name) for name in xls.sheet_names}
            found = {}

            for name, df in dfs.items():
                df.columns = [normalize_column(col) for col in df.columns]

                # 动态判断每张表的时间列
                possible_date_cols = ["截止日期", "报表截止日"]
                index_column = None
                for col in possible_date_cols:
                    if col in df.columns:
                        index_column = col
                        break
                if not index_column:
                    continue  # 如果没找到时间列就跳过

                df[index_column] = pd.to_datetime(df[index_column], format="%y/%m/%d", errors='coerce')
                df = df[df[index_column].dt.year >= 2000]
                df["年份"] = df[index_column].dt.year.astype(str)
                # 处理可能的重复年份 - 保留第一条记录
                df = df.drop_duplicates(subset="年份", keep="first")
                df.set_index("年份", inplace=True)

                for key, aliases in RAW_COLUMNS.items():
                    if key not in found:
                        col = find_column(df, aliases)
                        if col:
                            temp = df[[col]].rename(columns={col: key})
                            temp["__source__"] = f"{name} → {col}"
                            temp.index.name = "年份"
                            found[key] = temp


            if len(found) < 4:
                return app, None, [], "❌ 数据中无法找到用于计算 ROE 的所有必要字段"

            merged = pd.concat([found[k] for k in ["net_profit", "revenue", "total_assets", "equity"]], axis=1)
            source_logs = {k: found[k]["__source__"].iloc[0] for k in found if "__source__" in found[k].columns}
            merged.drop(columns=["__source__"], inplace=True, errors='ignore')
            merged.dropna(inplace=True)

            merged["净利润率"] = merged["net_profit"] / merged["revenue"]
            merged["资产周转率"] = merged["revenue"] / merged["total_assets"]
            merged["权益乘数"] = merged["total_assets"] / merged["equity"]
            merged["roa"] = merged["net_profit"] / merged["total_assets"]

            cached_df = merged
            cached_years = merged.index.unique().tolist()
            data_loaded = True
        except Exception as e:
            print(f"❌ 加载 Excel 异常: {e}")

   

    # 更新布局的回调函数
    @app.callback(
        Output('main-container', 'children'),
        Input('init-trigger', 'data')
    )
    def update_layout(_):
        print("🔄 触发布局更新回调")
        if not cached_years:
            print("⚠️ 没有可用的年份数据")
            return html.Div("❌ 未能加载有效数据，请检查Excel文件格式")
            
        print(f"✅ 准备显示数据，可用年份: {cached_years}")
        return html.Div([
            html.H2("📊 杜邦分析 - 树状图可视化（自动读取 Excel）"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': y, 'value': y} for y in cached_years],
                placeholder='请选择年份',
                value=cached_years[0] if cached_years else None
            ),
        html.Div([
                html.Iframe(id='tree-graph', width="100%", height="600"),
                html.Pre(id='source-log', style={'whiteSpace': 'pre-wrap', 'color': 'gray'}),
                html.Div(id='formula-display', style={
                    'marginTop': '20px',
                    'padding': '15px',
                    'backgroundColor': '#f5f5f5',
                    'borderRadius': '5px',
                    'border': '1px solid #ddd'
                }),
                html.Button('安全退出', id='close-button', style={
                    'marginTop': '20px',
                    'padding': '10px 20px',
                    'backgroundColor': '#ff4d4f',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer'
                })
            ])
        ])

    # 设置初始布局
    app.layout = html.Div([
        dcc.Store(id='init-trigger', data={'timestamp': pd.Timestamp.now().value}),
        html.Div(id='main-container', children=[
            html.Div("正在加载数据...", style={'fontSize': '18px', 'textAlign': 'center', 'marginTop': '50px'})
        ]),
    ])


    print(">>> create_app 完成")
    print(">>> layout 设置状态:", app.layout is not None)
    print(">>> cached_years =", cached_years)

    # 下拉菜单回调分析
    @app.callback(
        Output('tree-graph', 'srcDoc'),
        Output('source-log', 'children'),
        Output('formula-display', 'children'),
        Input('year-dropdown', 'value')
    )
    def update_chart(year):
        global source_logs
        if not year or cached_df is None:
            return "<p>请先上传数据并选择年份</p>", "", html.Div()
        try:
            row = cached_df.loc[year]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            net_profit_margin = row["净利润率"]
            asset_turnover = row["资产周转率"]
            equity_multiplier = row["权益乘数"]
            roa = row["net_profit"]/row['total_assets']
            roe = net_profit_margin * asset_turnover * equity_multiplier

            from pyecharts.charts import Tree
            from pyecharts import options as opts

            # 定义颜色和线宽
            # 定义颜色、线宽和节点样式
            color_level1 = "#5CACEE"  # 亮蓝色
            color_level2 = "#FF8C00"  # 橙色
            color_level3 = "#90EE90"  # 亮绿色
            color_leaf = "#B0C4DE"   # 浅钢蓝色 (叶子节点)
            width_level1 = 2
            width_level2 = 1.5
            width_level3 = 1
            border_color = "#FFFFFF" # 节点边框颜色
            border_width = 1        # 节点边框宽度

            # 定义节点样式
            item_style_level1 = {"color": color_level1, "borderColor": border_color, "borderWidth": border_width}
            item_style_level2 = {"color": color_level2, "borderColor": border_color, "borderWidth": border_width}
            item_style_level3 = {"color": color_level3, "borderColor": border_color, "borderWidth": border_width}
            item_style_leaf = {"color": color_leaf, "borderColor": border_color, "borderWidth": border_width}


            data = [
                {
                    "name": f"净资产收益率: {roe:.2%}",
                    "lineStyle": {"color": color_level1, "width": width_level1},
                    "itemStyle": item_style_level1,
                    "children": [
                        {
                            "name": f"总资产收益率: {roa:.2%}",
                            "lineStyle": {"color": color_level2, "width": width_level2},
                            "itemStyle": item_style_level2,
                            "children": [
                                {
                                    "name": f"净利润率: {net_profit_margin:.2%}",
                                    "lineStyle": {"color": color_level3, "width": width_level3},
                                    "itemStyle": item_style_level3,
                                    "children": [
                                        {"name": f"净利润: {row['net_profit']:.2f}", "itemStyle": item_style_leaf},
                                        {"name": f"营业收入: {row['revenue']:.2f}", "itemStyle": item_style_leaf}
                                    ]
                                },
                                {
                                    "name": f"资产周转率: {asset_turnover:.2f}",
                                    "lineStyle": {"color": color_level3, "width": width_level3},
                                    "itemStyle": item_style_level3,
                                    "children": [
                                        {"name": f"营业收入: {row['revenue']:.2f}", "itemStyle": item_style_leaf},
                                        {"name": f"总资产: {row['total_assets']:.2f}", "itemStyle": item_style_leaf}
                                    ]
                                }
                            ]
                        },
                        {
                            "name": f"权益乘数: {equity_multiplier:.2f}",
                            "lineStyle": {"color": color_level2, "width": width_level2},
                            "itemStyle": item_style_level2,
                            "children": [
                                {"name": f"总资产: {row['total_assets']:.2f}", "itemStyle": item_style_leaf},
                                {"name": f"股东权益: {row['equity']:.2f}", "itemStyle": item_style_leaf}
                            ]
                        }
                    ]
                }
            ]

            tree = (
                Tree(init_opts=opts.InitOpts(width="100%", height="600px", theme="chalk"))
                .add(
                    series_name="杜邦分解树",
                    data=data,
                    orient="LR",
                    symbol="circle",  # 改为圆形节点
                    symbol_size=20, # 调整节点大小
                    initial_tree_depth=-1,
                    label_opts=opts.LabelOpts(
                        position="left",
                        vertical_align="middle",
                        font_size=16,
                        font_weight="bold",
                        color="white"
                    )
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(
                        title=f"杜邦分析（{year}年）",
                        subtitle="点击节点可展开/折叠",
                        title_textstyle_opts=opts.TextStyleOpts(
                            font_size=20,
                            color="#333"
                        ),
                        subtitle_textstyle_opts=opts.TextStyleOpts(
                            font_size=14,
                            color="#999"
                        )
                    ),
                    tooltip_opts=opts.TooltipOpts(
                        trigger="item",
                        formatter="{b}"
                    )
                )
            )

            log_text = '\n'.join([f"{k}: {v}" for k, v in source_logs.items()])
            formula_html = html.Div([
                html.H4("计算公式:", style={'marginBottom': '10px'}),
                html.P(f"净资产收益率(ROE) = 净利润率 × 资产周转率 × 权益乘数 = {net_profit_margin:.2%} × {asset_turnover:.2f} × {equity_multiplier:.2f} = {roe:.2%}"),
                html.P(f"总资产收益率(ROA) = 净利润 / 总资产 = {row['net_profit']:.2f} / {row['total_assets']:.2f} = {roa:.2%}"),
                html.P(f"净利润率 = 净利润 / 营业收入 = {row['net_profit']:.2f} / {row['revenue']:.2f} = {net_profit_margin:.2%}"),
                html.P(f"资产周转率 = 营业收入 / 总资产 = {row['revenue']:.2f} / {row['total_assets']:.2f} = {asset_turnover:.2f}"),
                html.P(f"权益乘数 = 总资产 / 股东权益 = {row['total_assets']:.2f} / {row['equity']:.2f} = {equity_multiplier:.2f}")
            ])

            return tree.render_embed(), log_text, formula_html
        except Exception as e:
            return f"<p>图表生成失败: {e}</p>", "", html.Div()

    # 退出按钮
    @app.callback(
        Output('close-button', 'n_clicks'),
        Input('close-button', 'n_clicks')
    )
    def close_program(n_clicks):
        if n_clicks:
            import os
            os._exit(0)
        raise dash.exceptions.PreventUpdate

    return app, cached_df, cached_years

PRECOMPUTED_COLUMNS = {
    "net_profit_margin": "净利率(%)",
    "asset_turnover": "总资产周转率(次)",
    "equity_multiplier": "权益乘数",
    "return_on_total_assets":"总资产收益率(%)"

}

RAW_COLUMNS = {
    "net_profit": [
        "净利润", "归母净利润(元)", "税后净利润", "本公司股东应占利润", "除税后溢利:亏损","除税后溢利:除税后溢利",
        "持续经营净利润", "净收益", "Net Profit", "Net_Profit",
        "Net Income", "Profit attributable to owners"
    ],
    "revenue": [
        "营业收入", "营业收入合计", "营业收入总计", "营业收入共计", "营业总收入", "主营业务收入", "总收入", "营收",
        "销售收入", "商品销售收入", "营业总收入(元)", "营运收入合计", "营运收入总计", "营运收入共计", "Revenue",
        "Operating Revenue", "Operating_Income", "Sales"
    ],
    "total_assets": [
        "总资产", "资产合计", "资产总计", "合计资产", "总计资产",
        "Total Assets", "Total_Assets", "资产总额"
    ],
    "equity": [
        "股东权益", "净资产", "归属于母公司股东权益", "所有者权益",
        "权益总额","权益总计","权益总和","权益合计","权益共计","共计权益","合计权益","总计权益",
        "资本及储备", "本公司股东应占资本及储备", "Shareholders' Equity",
        "Equity", "Owners' Equity", "Equity attributable to owners"
    ]
}

def normalize_column(colname):
    if isinstance(colname, str):
        return zhconv.convert(colname.strip().replace("：", ":").replace("　", ""), 'zh-cn')
    return colname

def find_column(df, aliases):
    norm_cols = {normalize_column(col): col for col in df.columns}
    for alias in aliases:
        norm_alias = normalize_column(alias)
        if norm_alias in norm_cols:
            return norm_cols[norm_alias]
    return None

source_logs = {}

def run_app(app):
    import webbrowser
    from threading import Timer
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050/")
    
    # 确保布局已设置
    if app.layout is None:
        app.layout = html.Div("加载中...")
    
    Timer(1, open_browser).start()
    app.run(debug=False)

if __name__ == '__main__':
    app, _, _ = create_app()
    run_app(app)
