# Modified Agent Architecture

这是一个修改后的多智能体系统，基于Qwen Agent框架，实现了Controller-SubAgent协作模式。

## 主要特性

### 1. Controller设计
- **直接工具访问限制**: Controller只能直接调用 `search`、`visit`、`code` 三个工具
- **完整工具schema**: Controller拥有所有可用工具的schema信息，用于指定SubAgent可使用的工具
- **内部消息历史**: 使用 `self.messages` 存储对话历史，无需外部管理
- **统一输出格式**: 
  - 工具调用: `<tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>`
  - SubAgent创建: `<subagent>{"role": "role_name", "task": "task_description", "tools": ["tool1", "tool2"]}</subagent>`
  - 最终答案: `<answer>your answer</answer>`

### 2. SubAgent设计
- **任务专用性**: 每个SubAgent专注于特定角色和任务
- **工具限制**: 只能使用Controller分配的工具
- **内部消息历史**: 独立的 `self.messages` 存储执行历史
- **自主执行**: 可进行多轮交互直到任务完成

### 3. 架构优势
- **职责分离**: Controller负责协调，SubAgent负责执行
- **灵活性**: 可动态创建专用SubAgent
- **可扩展性**: 易于添加新工具和角色
- **历史管理**: 内部消息历史管理，简化使用

## 文件结构

```
agent.py              # 主要的Controller和SubAgent类
prompt_base.py        # 提示词模板和增强功能
run_agent.py          # 运行示例和演示
README_AGENT.md       # 本文档
```

## 使用方法

### 基本使用

```python
from agent import Controller, SubAgent
from prompt_base import get_enhanced_controller_prompt

# 准备工具列表
all_tools = [SearchTool(), VisitTool(), CodeTool(), AnalyzeTool()]

# 创建LLM配置
llm_cfg = {
    'model': 'your_model_path',
    'api_key': 'your_api_key',
    'model_server': 'your_server_url',
    'temperature': 0.6
}

# 创建Controller
controller = Controller(all_tools, llm_cfg)

# 执行任务
result = controller.step("Find information about Python web scraping")
print(result)
```

### 输出格式示例

#### Controller直接调用工具
```
<tool_call>{"name": "search", "arguments": {"query": "Python web scraping tutorials"}}</tool_call>
```

#### Controller创建SubAgent
```
<subagent>{"role": "Research Specialist", "task": "Find comprehensive information about web scraping libraries", "tools": ["search", "visit"]}</subagent>
```

#### SubAgent工具调用
```
<tool_call>{"name": "search", "arguments": {"query": "BeautifulSoup vs Scrapy comparison"}}</tool_call>
```

#### 最终答案
```
<answer>Based on my research, here are the top Python web scraping libraries...</answer>
```

## 运行示例

### 命令行运行
```bash
# 运行特定任务
python run_agent.py --task "Research latest AI developments"

# 运行演示场景
python run_agent.py --demo

# 交互模式
python run_agent.py
```

### 演示场景
运行示例包含三个预设场景：
1. **简单搜索任务**: 搜索Python库并推荐
2. **复杂研究任务**: AI模型发展研究和分析
3. **多步编程任务**: 创建天气数据爬虫脚本

## 工具系统

### Controller可直接使用的工具
- `search`: 网络搜索
- `visit`: 访问特定URL
- `code`: 代码生成和分析

### 所有可用工具 (用于SubAgent分配)
- `search`: 搜索工具
- `visit`: 网页访问工具
- `code`: 代码工具
- `analyze`: 数据分析工具
- `summarize`: 文本摘要工具

## SubAgent角色类型

系统预定义了几种专用角色：

### Research Specialist
- **专长**: 信息收集和验证
- **常用工具**: search, visit
- **适用场景**: 研究任务、信息查找

### Analysis Specialist  
- **专长**: 数据分析和解释
- **常用工具**: analyze, search
- **适用场景**: 数据处理、趋势分析

### Developer
- **专长**: 代码开发和优化
- **常用工具**: code, search
- **适用场景**: 编程任务、代码审查

### Content Specialist
- **专长**: 内容创建和组织
- **常用工具**: summarize, search
- **适用场景**: 内容整理、文档编写

## 配置说明

### LLM配置
```python
llm_cfg = {
    'model': 'model_path_or_name',           # 模型路径或名称
    'api_key': 'your_api_key',               # API密钥
    'model_server': 'http://server:port/v1', # 服务器地址
    'temperature': 0.6,                      # 生成温度
    'generate_cfg': {                        # 生成配置
        'temperature': 0.6,
        'top_p': 0.95
    }
}
```

### 工具配置
工具需要实现以下接口：
```python
class CustomTool:
    def __init__(self):
        self.name = "tool_name"              # 工具名称
        self.description = "tool description" # 工具描述
        self.parameters = {...}              # 参数schema
    
    def call(self, **kwargs):               # 工具调用方法
        # 实现工具逻辑
        return result
```

## 最佳实践

### 1. 任务分解
- 复杂任务优先考虑创建专用SubAgent
- 简单操作可直接使用Controller工具

### 2. 工具分配
- 根据SubAgent角色合理分配工具
- 避免分配不必要的工具

### 3. 错误处理
- 系统内置错误处理机制
- 建议添加重试逻辑

### 4. 性能优化
- 合理设置最大轮次限制
- 监控消息历史长度

## 注意事项

1. **工具限制**: Controller只能直接使用search、visit、code三个工具
2. **消息历史**: 系统自动管理内部消息历史，无需手动维护
3. **SubAgent生命周期**: SubAgent在任务完成后会返回结果给Controller
4. **LLM配置**: 确保LLM服务器正确配置和可访问
5. **工具实现**: 确保所有工具正确实现call方法

## 扩展指南

### 添加新工具
1. 创建工具类，实现必要接口
2. 将工具添加到all_tools列表
3. 更新prompt中的工具描述

### 添加新角色
1. 在SUBAGENT_ROLE_PROMPTS中添加角色定义
2. 设计适合的工具组合
3. 测试角色专用性

### 自定义提示词
1. 修改prompt_base.py中的模板
2. 使用get_enhanced_*_prompt函数
3. 测试提示词效果

这个架构提供了灵活、可扩展的多智能体协作框架，适合处理各种复杂任务。