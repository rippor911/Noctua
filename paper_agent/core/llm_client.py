"""
LLM客户端模块 - 封装OpenAI API调用

参考 paper-qa 的最佳实践，改进：
1. 使用结构化的提示词模板
2. 支持JSON模式输出
3. 更严格的幻觉控制
4. 更好的错误处理
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Generator, Union
from dataclasses import dataclass
from enum import Enum

from . import prompts


class ModelProvider(Enum):
    """支持的模型提供商"""
    OPENAI = "openai"
    AZURE = "azure"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: ModelProvider = ModelProvider.OPENAI
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.2  # 更低温度减少幻觉
    max_tokens: int = 4000
    timeout: int = 60
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.base_url:
            self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


@dataclass
class Message:
    """消息结构"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM响应结构"""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str


class LLMClient:
    """LLM客户端"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
        except ImportError:
            raise ImportError("请安装OpenAI SDK: pip install openai")
    
    def chat(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数（覆盖配置）
            max_tokens: 最大token数（覆盖配置）
            stream: 是否流式输出
            json_mode: 是否强制JSON输出
            
        Returns:
            LLM响应
        """
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")
        
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        # 转换消息格式
        formatted_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        try:
            kwargs = {
                "model": self.config.model,
                "messages": formatted_messages,
                "temperature": temp,
                "max_tokens": max_tok,
                "stream": stream
            }
            
            # 如果支持JSON模式，添加响应格式
            if json_mode and "gpt-4" in self.config.model:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            if stream:
                return self._handle_streaming_response(response)
            
            return LLMResponse(
                content=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Exception as e:
            raise RuntimeError(f"LLM API调用失败: {str(e)}")
    
    def _handle_streaming_response(self, response) -> LLMResponse:
        """处理流式响应"""
        content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
        
        return LLMResponse(
            content=content,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            model=self.config.model,
            finish_reason="stop"
        )
    
    def chat_stream(
        self, 
        messages: List[Message], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """
        流式聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            内容片段
        """
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")
        
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        formatted_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=formatted_messages,
                temperature=temp,
                max_tokens=max_tok,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise RuntimeError(f"LLM流式API调用失败: {str(e)}")
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """
        生成文本摘要 - 使用优化提示词
        
        Args:
            text: 输入文本
            max_length: 摘要最大长度
            
        Returns:
            摘要文本
        """
        user_prompt = prompts.SUMMARY_PROMPT.format(
            text=text[:10000],
            max_length=max_length
        )
        
        messages = [
            Message(role="user", content=user_prompt)
        ]
        
        response = self.chat(messages, temperature=0.3)
        return response.content.strip()
    
    def extract_key_points(self, text: str) -> List[str]:
        """
        提取关键点 - 使用优化提示词
        
        Args:
            text: 输入文本
            
        Returns:
            关键点列表
        """
        user_prompt = prompts.KEY_POINTS_PROMPT.format(text=text[:10000])
        
        messages = [
            Message(role="user", content=user_prompt)
        ]
        
        response = self.chat(messages, temperature=0.3)
        points = [p.strip() for p in response.content.split('\n') if p.strip()]
        # 清理编号
        points = [re.sub(r'^\d+[.\s]+', '', p) for p in points]
        return points[:10]
    
    def analyze_paper_structure(self, text: str) -> Dict[str, Any]:
        """
        分析论文结构 - 使用优化提示词和JSON模式
        
        Args:
            text: 论文文本
            
        Returns:
            论文结构分析
        """
        user_prompt = prompts.PAPER_STRUCTURE_PROMPT.format(text=text[:12000])
        
        messages = [
            Message(role="user", content=user_prompt)
        ]
        
        try:
            response = self.chat(messages, temperature=0.2, json_mode=True)
            return json.loads(response.content)
        except (json.JSONDecodeError, Exception) as e:
            # 如果JSON解析失败，尝试提取JSON部分
            try:
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return json.loads(content.strip())
            except:
                return {
                    "raw_analysis": response.content,
                    "parse_error": True,
                    "error": str(e)
                }
    
    def answer_with_citation(
        self, 
        question: str, 
        context: str,
        require_citation: bool = True
    ) -> Dict[str, Any]:
        """
        基于上下文回答问题，并标注引用来源 - 使用严格学术提示词
        
        Args:
            question: 问题
            context: 上下文文本
            require_citation: 是否要求标注引用
            
        Returns:
            包含答案和引用的字典
        """
        system_prompt = prompts.QA_SYSTEM_PROMPT.format(
            CITATION_CONSTRAINTS=prompts.CITATION_CONSTRAINTS
        )
        
        user_prompt = prompts.QA_USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question
        )
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = self.chat(messages, temperature=0.2)
        answer_text = response.content
        
        # 检测是否无法回答
        is_answerable = not any(
            phrase in answer_text.lower() 
            for phrase in [p.lower() for p in prompts.CANNOT_ANSWER_PHRASES]
        )
        
        # 确定置信度
        confidence = "high" if is_answerable else "low"
        if is_answerable and any(
            marker in answer_text.lower() 
            for marker in ["可能", "也许", "大概", "似乎", "应该"]
        ):
            confidence = "medium"
        
        return {
            "answer": answer_text,
            "has_citation": require_citation,
            "confidence": confidence,
            "is_answerable": is_answerable
        }
    
    def verify_answer(
        self,
        answer: str,
        context: str
    ) -> Dict[str, Any]:
        """
        验证答案的准确性
        
        Args:
            answer: 待验证的答案
            context: 原始上下文
            
        Returns:
            验证结果
        """
        user_prompt = prompts.ANSWER_VERIFICATION_PROMPT.format(
            answer=answer,
            context=context[:5000]
        )
        
        messages = [
            Message(role="user", content=user_prompt)
        ]
        
        try:
            response = self.chat(messages, temperature=0.1, json_mode=True)
            return json.loads(response.content)
        except:
            return {
                "is_valid": True,
                "issues": [],
                "confidence": "medium"
            }
    
    def decompose_question(self, question: str) -> List[str]:
        """
        分解复杂问题
        
        Args:
            question: 复杂问题
            
        Returns:
            子问题列表
        """
        user_prompt = prompts.QUESTION_DECOMPOSITION_PROMPT.format(question=question)
        
        messages = [
            Message(role="user", content=user_prompt)
        ]
        
        response = self.chat(messages, temperature=0.3)
        sub_questions = [
            q.strip() for q in response.content.split('\n')
            if q.strip() and not q.strip().startswith('```')
        ]
        return sub_questions[:4]
    
    def synthesize_answers(
        self,
        question: str,
        sub_qa_pairs: List[Dict[str, str]]
    ) -> str:
        """
        综合子问题答案
        
        Args:
            question: 原始问题
            sub_qa_pairs: 子问题-答案对列表
            
        Returns:
            综合答案
        """
        qa_text = "\n\n".join([
            f"子问题{i+1}: {pair['question']}\n答案: {pair['answer']}"
            for i, pair in enumerate(sub_qa_pairs)
        ])
        
        user_prompt = prompts.SYNTHESIS_PROMPT.format(
            question=question,
            sub_qa_pairs=qa_text
        )
        
        messages = [
            Message(role="user", content=user_prompt)
        ]
        
        response = self.chat(messages, temperature=0.3)
        return response.content


def create_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> LLMClient:
    """
    创建LLM客户端的便捷函数
    
    Args:
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        
    Returns:
        LLMClient实例
    """
    config = LLMConfig(
        api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=model,
        temperature=0.2,  # 更低温度减少幻觉
        max_tokens=4000
    )
    return LLMClient(config)
