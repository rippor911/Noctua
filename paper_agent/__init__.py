"""
Paper Agent - 论文智能体

一个能够读论文、做笔记、建数据库的智能系统，
支持基于检索增强生成（RAG）的无幻觉问答。

参考项目：
- paper-qa: 严谨的学术引用和问答
- mad-professor: 全面的笔记生成
- Paper2Agent: 智能论文处理

主要功能：
- PDF论文解析（支持元数据提取）
- 自动生成结构化笔记（方法、实验、结果分离）
- 向量数据库存储
- 无幻觉问答（带引用）
- 多跳复杂问题推理

示例用法：
    from paper_agent import create_agent
    
    # 创建智能体（自动从.env读取配置）
    agent = create_agent()
    
    # 处理论文
    result = agent.process_paper("path/to/paper.pdf")
    
    # 问答（带引用）
    answer = agent.ask("论文的主要贡献是什么？")
    print(answer["answer"])
    print(f"引用: {answer['citations']}")
"""

from .paper_agent import PaperAgent, AgentConfig, create_agent
from .core import (
    # PDF解析
    PDFParser, PyMuPDFParser, SimplePDFParser, get_parser,
    ParsedPaper, PaperSection, PaperMetadata, Citation,
    Table, Figure, SectionType,
    # LLM客户端
    LLMClient, LLMConfig, Message, LLMResponse, create_client,
    # 笔记管理
    NoteManager, NoteGenerator, Note, NoteType, SectionNote,
    # 向量存储
    VectorStore, ChromaVectorStore, SimpleVectorStore,
    TextChunker, DocumentChunk, create_vector_store,
    # 问答系统
    QASystem, MultiHopQA, Answer, RetrievedContext,
    # 提示词
    prompts,
)

__version__ = "0.2.0"
__author__ = "Paper Agent Team"

__all__ = [
    # 主类
    'PaperAgent',
    'AgentConfig',
    'create_agent',
    
    # PDF解析
    'PDFParser',
    'PyMuPDFParser',
    'SimplePDFParser',
    'get_parser',
    'ParsedPaper',
    'PaperSection',
    'PaperMetadata',
    'Citation',
    'Table',
    'Figure',
    'SectionType',
    
    # LLM客户端
    'LLMClient',
    'LLMConfig',
    'Message',
    'LLMResponse',
    'create_client',
    
    # 笔记管理
    'NoteManager',
    'NoteGenerator',
    'Note',
    'NoteType',
    'SectionNote',
    
    # 向量存储
    'VectorStore',
    'ChromaVectorStore',
    'SimpleVectorStore',
    'TextChunker',
    'DocumentChunk',
    'create_vector_store',
    
    # 问答系统
    'QASystem',
    'MultiHopQA',
    'Answer',
    'RetrievedContext',
    
    # 提示词
    'prompts',
]
