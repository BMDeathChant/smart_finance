"""
Deepseek API封装工具
提供简化的Deepseek API调用接口
支持聊天补全和数据分析功能
"""

# 标准库
import logging  # 日志记录
import json  # JSON处理
from typing import Optional, Dict, List, Union, Any  # 类型提示
from dataclasses import dataclass  # 数据类装饰器

# 第三方库
import openai  # OpenAI API客户端
import pandas as pd  # 数据分析处理

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Markdown 输出规范指南
MARKDOWN_GUIDELINES = """
从现在开始，输出的 Markdown 必须满足以下要求：

1. **标题**：使用 `#` 到 `######`，前后各空一行。
2. **子标题编号**：  
   - 每当出现二级标题 `## X. 标题` 时，其下一级标题请使用 `### X.1 子标题`、`### X.2 子标题` 等格式，X 与二级标题的编号保持一致，数字从 1 开始递增。  
3. **有序列表**：每级都用 `1. `、`2. ` …；嵌套时，子项目前缩进 **2 个空格**，并在父级项目和子列表之间留一空行。  
4. **无序列表**：用 `- `（中划线后跟空格），在列表项前后都留一空行；嵌套时，同样缩进 **2 个空格**。  
   - **注意**：`-` 与内容之间**必须**有一个空格，否则容易被当成普通段落或导致断行错位。
5. **段落**：每个段落前后空一行，不要直接粘在列表或标题后。
6. **分隔线**：用三条短横 `---`，前后空行。不要用 HTML `<hr>`。
7. **避免内嵌原始 HTML**：一律用 Markdown 语法。
8. **表格**：用标准的管道表格语法，表头与分隔行前后各空行。
9. **代码块**：不允许输出代码块
请严格遵守以上规则生成最终报告，保证缩进和空行正确。
"""

@dataclass
class AnalysisResult:
    """数据分析结果容器"""
    summary: str
    insights: List[str]
    recommendations: List[str]
    raw_response: str

class DataAnalyzer:
    """数据分析工具类
    
    提供标准化的数据分析功能，支持:
    - 数据概览分析
    - 趋势分析
    - 异常检测
    - 预测建议
    """
    
    def __init__(self, llm_client: Any):
        """初始化分析器
        
        Args:
            llm_client: 语言模型客户端(需实现chat_completion接口)
        """
        self.client = llm_client
        
    def analyze(
        self,
        df: pd.DataFrame,
        task: str = "standard",
        custom_prompt: Optional[str] = None,
        output_md: Optional[str] = None
    ) -> AnalysisResult:
        """执行数据分析
        
        Args:
            df: 输入DataFrame
            task: 分析类型(standard/trend/anomaly)
            custom_prompt: 自定义分析提示
            output_md: 输出MD文件路径(可选)
            
        Returns:
            AnalysisResult对象
            
        Raises:
            ValueError: 当输入数据无效时
            Exception: API调用失败时
        """
        if df.empty:
            raise ValueError("输入DataFrame不能为空")
            
        # 生成系统提示
        system_prompt = self._get_system_prompt(task) + "\n\n" + MARKDOWN_GUIDELINES
        
        # 准备数据样本
        sample = df.head(3).to_markdown()
        stats = df.describe().to_markdown()
        
        # 构建用户提示
        user_prompt = custom_prompt or self._get_default_prompt(task)
        full_prompt = f"{user_prompt}\n\n数据样本:\n{sample}\n\n统计信息:\n{stats}"
        
        # 调用API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        
        response = self.client.chat_completion(messages)
        result = self._parse_response(response)
        
        if output_md:
            self._save_md_report(result, output_md)
            
        return result
        
    def _get_system_prompt(self, task: str) -> str:
        """获取系统提示模板"""
        prompts = {
            "standard": "你是一个资深财务数据分析师，请专业地分析财务数据",
            "trend": "你擅长发现财务数据趋势和模式",
            "anomaly": "你擅长检测财务数据异常和离群值",
            "balance_sheet": "你是财务专家，请分析资产负债表的关键指标",
            "income_statement": "你是财务专家，请分析利润表的盈利能力和经营效率", 
            "cash_flow": "你是财务专家，请分析现金流量表的资金流动情况",
            "financial_metrics": "你是财务分析专家，请深入分析主要财务指标"
        }
        return prompts.get(task, prompts["standard"])
        
    def _get_default_prompt(self, task: str) -> str:
        """获取默认用户提示"""
        prompts = {
            "standard": "请分析这份财务数据并给出关键结论",
            "trend": "请分析财务数据趋势和周期性模式", 
            "anomaly": "请检测财务数据中的异常值并解释原因",
            "balance_sheet": """
                请分析以下资产负债表指标：
                1. 资产结构和负债结构的合理性
                2. 流动比率和速动比率
                3. 资产负债率变化趋势
                4. 关键异常值和可能原因
            """,
            "income_statement": """
                请分析以下利润表指标：
                1. 营业收入增长率和毛利率变化
                2. 三项费用(销售/管理/财务费用)占比
                3. 净利润率和ROE变化
                4. 异常波动项目和可能原因
            """,
            "cash_flow": """
                请分析以下现金流量表指标：
                1. 经营活动现金流净额与净利润的匹配度
                2. 投资活动现金流的主要去向
                3. 筹资活动现金流的来源和用途
                4. 自由现金流计算和分析
            """,
            "financial_metrics": """
                请分析以下主要财务指标：
                1. 每股收益(EPS)及其变化趋势
                2. 净资产收益率(ROE)和总资产收益率(ROA)
                3. 毛利率、营业利润率和净利润率
                4. 市盈率(PE)和市净率(PB)估值指标
                5. 关键指标的行业对比和变化原因
            """
        }
        return prompts.get(task, prompts["standard"])
        
    def _parse_response(self, response: str) -> AnalysisResult:
        """解析API响应"""
        # 这里可以添加更复杂的解析逻辑
        return AnalysisResult(
            summary=response,
            insights=[],
            recommendations=[],
            raw_response=response
        )
        
    def _save_md_report(self, result: AnalysisResult, file_path: str) -> None:
        """保存分析结果为MD文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# 数据分析报告\n\n")
            f.write(f"## 摘要\n{result.summary}\n\n")
            if result.insights:
                f.write(f"## 关键洞察\n")
                for insight in result.insights:
                    f.write(f"- {insight}\n")
                f.write("\n")
            if result.recommendations:
                f.write(f"## 建议\n")
                for rec in result.recommendations:
                    f.write(f"- {rec}\n")
                f.write("\n")
                
    def analyze_excel(self, excel_path: str, output_dir: str) -> Dict[str, AnalysisResult]:
        """分析Excel文件的所有sheet并生成MD报告
        
        Args:
            excel_path: Excel文件路径
            output_dir: 输出目录
            
        Returns:
            包含每个sheet分析结果的字典
        """
        results = {}
        with pd.ExcelFile(excel_path) as xls:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                result = self.analyze(
                    df,
                    output_md=f"{output_dir}/{sheet_name}_analysis.md"
                )
                results[sheet_name] = result
        return results

    def analyze_combined(
        self, 
        sheets_data: Dict[str, pd.DataFrame],
        output_md: Optional[str] = None
    ) -> AnalysisResult:
        """合并分析多个sheet的数据
        
        Args:
            sheets_data: 包含sheet名称和对应DataFrame的字典
            output_md: 输出MD文件路径(可选)
            
        Returns:
            合并分析结果
        """
        if not sheets_data:
            raise ValueError("输入数据不能为空")
            
        # 生成系统提示
        system_prompt = "你是一个资深财务分析师，请综合分析资产负债表、利润表和现金流量表"
        
        # 准备数据样本
        samples = []
        for sheet_name, df in sheets_data.items():
            sample = df.head(3).to_markdown()
            samples.append(f"=== {sheet_name} 样本 ===\n{sample}")
        
        # 构建用户提示
        user_prompt = """
            请综合分析以下财务报表:
            1. 评估公司整体财务状况
            2. 分析三张报表之间的勾稽关系
            3. 识别关键财务指标间的矛盾点
            4. 给出综合性的财务健康度评估
            5. 提供改进建议
        """
        full_prompt = f"{user_prompt}\n\n" + "\n\n".join(samples)
        
        # 调用API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        
        response = self.client.chat_completion(messages)
        result = self._parse_response(response)
        
        if output_md:
            self._save_md_report(result, output_md)
            
        return result

class AIDataAssistant:
    """AI数据助手(整合Deepseek API和分析功能)"""
    
    def __init__(self, api_key: str, organization: Optional[str] = None):
        """初始化AI助手
        
        Args:
            api_key: Deepseek API密钥
            organization: 组织ID(可选)
        """
        self.wrapper = DeepseekWrapper(api_key, organization)
        self.analyzer = DataAnalyzer(self.wrapper)
        logger.info("AI数据助手初始化完成")
    
    def analyze_data(self, df: pd.DataFrame, task: str = "standard") -> AnalysisResult:
        """执行数据分析(简化接口)
        
        Args:
            df: 输入DataFrame
            task: 分析类型(standard/trend/anomaly)
            
        Returns:
            AnalysisResult对象
        """
        return self.analyzer.analyze(df, task)
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全接口(直接转发到wrapper)
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数传递给DeepseekWrapper
            
        Returns:
            模型生成的文本
        """
        return self.wrapper.chat_completion(messages, **kwargs)
        
    def get_insights(self, df: pd.DataFrame) -> str:
        """获取数据洞察(简化接口)
        
        Args:
            df: 输入DataFrame
            
        Returns:
            包含数据洞察的文本
        """
        result = self.analyze_data(df)
        return result.summary

class DeepseekWrapper:
    """Deepseek API客户端封装"""
    
    def __init__(self, api_key: str, organization: Optional[str] = None):
        """初始化OpenAI客户端
        
        Args:
            api_key: OpenAI API密钥
            organization: 组织ID(可选)
        """
        self.client = openai.OpenAI(
            api_key=api_key,
            organization=organization,
            base_url="https://api.deepseek.com/v1"  # Deepseek API端点
        )
        logger.info("Deepseek客户端初始化完成")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",  # Deepseek模型名称
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """聊天补全接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            模型生成的文本
            
        Raises:
            openai.OpenAIError: API调用失败时抛出
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            logger.info(f"成功获取聊天补全结果，使用token数: {response.usage.total_tokens}")
            return content
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise
