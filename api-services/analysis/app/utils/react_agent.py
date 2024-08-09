from langchain.agents import Tool, create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from app.utils.analyze_tools import PythonCodeAnalysisTool, SQLAnalysisTool, SecurityVulnerabilityAnalysisTool, ReportTool
from app.utils.config_llm import config_llm

# 사용 가능한 도구 정의
tools = [
    Tool(name="Python Code Analysis",
         func=PythonCodeAnalysisTool()._run,
         description="Clone a GitHub repository and perform Bandit and PEP8 analysis. Takes GitHub URL, optional directory path, and optional PAT as input in the format 'github_url|Branch|Directory|PAT'."),
    Tool(name="SQL Analysis",
         func=SQLAnalysisTool()._run,
         description="Analyze SQL content from a GitHub repository using SQLCheck. Takes GitHub URL, optional directory path, and optional PAT as input in the format 'github_url|Branch|Directory|PAT'."),
    Tool(name="Security Vulnerability Analysis",
         func=SecurityVulnerabilityAnalysisTool()._run,
         description="Clone a GitHub repository and perform security analysis using Horusec. Takes GitHub URL, optional directory path, and optional PAT as input in the format 'github_url|Branch|Directory|PAT'."),
    Tool(name="Generate Report",
         func=ReportTool()._run,
         description="Generate a report based on the identifier value by searching related results in the vector store. Takes identifier value as input.")
]

# LLM 초기화
config_llm.initialize_llm_from_env()
llm = config_llm.get_llm()

# 프롬프트 템플릿 정의
template = '''
**Instructions**: 
- Create an analytical report based on the selected output format and provide it as the final answer. 

Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Selected Tool: the analysis tool to use, should be one of [{tool_names}]
Thought: you should always think about what to do. Do not generate the report here.
Action: the action to take, should be the selected tool from above
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know what to do. I will generate the report.
Final Answer: the final answer to the original input question, which includes the formatted report

Begin!

Question: {input}
Selected Tool: {analysis_tool}
Directory: {directory_path}
PAT: {pat}
Branch: {branch}
Report Format Type : {output_format}
Report Language : {output_language}
Thought:{agent_scratchpad}
'''

prompt = PromptTemplate.from_template(template)

# REACT 에이전트 생성
Analyzer_Agent = create_react_agent(llm, tools, prompt)

def agent():
    """
    구성된 REACT 에이전트와 도구들로 AgentExecutor를 초기화하고 반환합니다.
    """
    return AgentExecutor(
        agent=Analyzer_Agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=10
    )
