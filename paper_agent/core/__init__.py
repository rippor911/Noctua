"""
Paper Agent Core Module

核心模块包含：
- PDF解析
- LLM客户端
- 笔记管理
- 向量存储
- 问答系统
- 提示词模板
"""

from .pdf_parser import (
    PDFParser, PyMuPDFParser, SimplePDFParser, get_parser,
    ParsedPaper, PaperSection, PaperMetadata, Citation,
    Table, Figure, SectionType
)
from .llm_client import LLMClient, LLMConfig, Message, LLMResponse, create_client
from .note_manager import NoteManager, NoteGenerator, Note, NoteType, SectionNote
from .vector_store import (
    VectorStore, ChromaVectorStore, SimpleVectorStore,
    TextChunker, DocumentChunk, create_vector_store
)
from .qa_system import QASystem, MultiHopQA, Answer, RetrievedContext
from . import prompts

__all__ = [
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
