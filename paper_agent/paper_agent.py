"""
🦉 Noctua Paper Agent - 智慧猫头鹰论文阅读助手

整合所有模块，提供统一的论文处理接口
参考 paper-qa 和 mad-professor 的最佳实践

特色：
1. 拟人化猫头鹰形象
2. 基于时间的动态语气（白天困倦/夜晚精神）
3. 趣味进度反馈（咕咕咕进度条）
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from .core import (
    get_parser,
    create_client,
    NoteManager,
    NoteGenerator,
    create_vector_store,
    TextChunker,
    QASystem,
    MultiHopQA,
    ParsedPaper,
    NoteType,
)
from .noctua_personality import NoctuaPersonality, create_noctua


def _load_env_file():
    """加载 .env 文件"""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = value


# 程序启动时加载 .env 文件
_load_env_file()


@dataclass
class AgentConfig:
    """智能体配置"""
    # API配置
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    
    # 路径配置
    papers_dir: str = "./papers"
    notes_dir: str = "./notes"
    database_dir: str = "./database"
    
    # 处理配置
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k_retrieval: int = 5
    
    def __post_init__(self):
        # 优先级：传入值 > 环境变量 > .env文件（已加载到环境变量）
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.base_url:
            self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        # 模型从环境变量读取，如果没有设置则使用默认值
        self.model = os.getenv("MODEL", self.model)
        
        # 从环境变量读取目录配置
        self.papers_dir = os.getenv("PAPERS_DIR", self.papers_dir)
        self.notes_dir = os.getenv("NOTES_DIR", self.notes_dir)
        self.database_dir = os.getenv("DATABASE_DIR", self.database_dir)
        
        # 从环境变量读取处理配置
        self.chunk_size = int(os.getenv("CHUNK_SIZE", self.chunk_size))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", self.chunk_overlap))
        self.top_k_retrieval = int(os.getenv("TOP_K_RETRIEVAL", self.top_k_retrieval))


class PaperAgent:
    """
    论文智能体 - 主类
    
    功能：
    1. 读取PDF论文
    2. 生成结构化笔记
    3. 构建向量数据库
    4. 无幻觉问答
    """
    
    def __init__(self, config: Optional[AgentConfig] = None, noctua: Optional[NoctuaPersonality] = None):
        self.config = config or AgentConfig()
        
        # 初始化 Noctua 个性化（可选）
        self.noctua = noctua
        
        # 初始化目录
        self._init_directories()
        
        # 初始化组件
        self._init_components()
    
    def _init_directories(self):
        """初始化目录"""
        Path(self.config.papers_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.notes_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.database_dir).mkdir(parents=True, exist_ok=True)
    
    def _init_components(self):
        """初始化各个组件"""
        # PDF解析器
        self.parser = get_parser("pymupdf")
        
        # LLM客户端
        self.llm_client = create_client(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model
        )
        
        # 笔记管理器
        self.note_manager = NoteManager(self.config.notes_dir)
        self.note_generator = NoteGenerator(self.llm_client)
        
        # 向量存储
        self.vector_store = create_vector_store(
            store_type="chroma",
            persist_directory=os.path.join(self.config.database_dir, "chroma")
        )
        self.chunker = TextChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        # 问答系统
        self.qa_system = QASystem(self.llm_client, self.vector_store)
        self.multi_hop_qa = MultiHopQA(self.qa_system)
    
    def read_paper(self, file_path: str) -> ParsedPaper:
        """
        读取论文
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            ParsedPaper对象
        """
        if self.noctua and self.noctua.enabled:
            self.noctua.print_reaction()
            self.noctua.print_reading()
            print(f"[Noctua] 正在读取论文: {file_path}")
        else:
            print(f"正在读取论文: {file_path}")

        paper_data = self.parser.parse(file_path)

        if self.noctua and self.noctua.enabled:
            self.noctua.print_celebrating()
            print(f"[Noctua] 论文读取完成: {paper_data.file_name}")
        else:
            print(f"[完成] 论文读取完成: {paper_data.file_name}")
        return paper_data
    
    def create_note(
        self,
        paper_data: ParsedPaper,
        tags: List[str] = None,
        note_type: NoteType = NoteType.DETAILED
    ) -> Dict[str, Any]:
        """
        为论文创建笔记 - 增强版（带咕咕咕进度条）

        Args:
            paper_data: 论文解析数据
            tags: 标签列表
            note_type: 笔记类型

        Returns:
            笔记数据
        """
        # 定义进度回调函数
        def progress_callback(progress: float, step: str):
            if self.noctua and self.noctua.enabled:
                self.noctua.print_progress(progress, f"[Noctua] {step}")
            else:
                bar_length = 30
                filled = int(bar_length * progress)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(f"\r[{bar}] {progress*100:.1f}% - {step}", end="", flush=True)

        if self.noctua and self.noctua.enabled:
            print(f"[Noctua] {self.noctua.get_waiting_message()}")
            print(f"[Noctua] 开始生成笔记，请稍等咕~")
        else:
            print("正在生成笔记...")

        # 生成笔记内容（带进度回调）
        note_content = self.note_generator.generate_from_paper(
            {
                'full_text': paper_data.full_text,
                'sections': paper_data.sections,
                'metadata': paper_data.metadata
            },
            progress_callback=progress_callback
        )

        # 换行（进度条结束后）
        if not (self.noctua and self.noctua.enabled):
            print()
        
        # 创建笔记
        note = self.note_manager.create_note(
            paper_path=paper_data.file_path,
            paper_title=paper_data.file_name,
            paper_doi=paper_data.metadata.doi,
            paper_authors=paper_data.metadata.authors,
            summary=note_content['summary'],
            key_points=note_content['key_points'],
            sections=note_content['sections'],
            methodology=note_content['methodology'],
            experiments=note_content['experiments'],
            results=note_content['results'],
            conclusions=note_content['conclusions'],
            limitations=note_content['limitations'],
            tags=tags or [],
            note_type=note_type
        )
        
        # 从索引中获取文件名信息
        filename = note.id
        for note_info in self.note_manager.notes_index["notes"]:
            if note_info["id"] == note.id:
                filename = note_info.get("filename", note.id)
                break

        if self.noctua and self.noctua.enabled:
            print(f"[Noctua] 笔记创建完成!")
            print(f"   📄 JSON: {filename}.json")
            print(f"   📝 Markdown: {filename}.md")
        else:
            print(f"[完成] 笔记创建完成!")
            print(f"  JSON: {filename}.json")
            print(f"  Markdown: {filename}.md")
        return note.to_dict()
    
    def add_to_database(self, paper_data: ParsedPaper) -> bool:
        """
        将论文添加到向量数据库
        
        Args:
            paper_data: 论文解析数据
            
        Returns:
            是否添加成功
        """
        if self.noctua and self.noctua.enabled:
            print(f"[Noctua] 正在添加到向量数据库...")
        else:
            print("正在添加到向量数据库...")
        
        # 分块
        chunks = self.chunker.chunk_paper({
            'file_path': paper_data.file_path,
            'file_name': paper_data.file_name,
            'full_text': paper_data.full_text,
            'pages': paper_data.pages,
            'sections': paper_data.sections
        })
        
        if self.noctua and self.noctua.enabled:
            print(f"   生成 {len(chunks)} 个文本块")
        else:
            print(f"  生成 {len(chunks)} 个文本块")
        
        # 添加到向量库
        success = self.vector_store.add_documents(chunks)
        
        if self.noctua and self.noctua.enabled:
            if success:
                print(f"[Noctua] 成功添加到数据库")
            else:
                print(f"[Noctua] 添加到数据库失败")
        else:
            if success:
                print(f"[完成] 成功添加到数据库")
            else:
                print(f"[失败] 添加到数据库失败")
        
        return success
    
    def process_paper(
        self,
        file_path: str,
        create_note: bool = True,
        add_to_db: bool = True,
        tags: List[str] = None,
        note_type: NoteType = NoteType.DETAILED
    ) -> Dict[str, Any]:
        """
        处理论文（完整流程）
        
        Args:
            file_path: PDF文件路径
            create_note: 是否创建笔记
            add_to_db: 是否添加到数据库
            tags: 标签列表
            note_type: 笔记类型
            
        Returns:
            处理结果
        """
        result = {
            "file_path": file_path,
            "success": False,
            "paper_data": None,
            "note": None,
            "db_added": False
        }
        
        try:
            # 1. 读取论文
            paper_data = self.read_paper(file_path)
            result["paper"] = {
                "file_path": paper_data.file_path,
                "file_name": paper_data.file_name,
                "doc_id": paper_data.doc_id,
                "total_pages": len(paper_data.pages),
                "metadata": {
                    "title": paper_data.metadata.title,
                    "authors": paper_data.metadata.authors,
                    "doi": paper_data.metadata.doi,
                    "abstract": paper_data.metadata.abstract[:200] + "..." if paper_data.metadata.abstract else ""
                }
            }
            # 保留旧字段名兼容
            result["paper_data"] = result["paper"]
            
            # 2. 创建笔记
            if create_note:
                note = self.create_note(paper_data, tags=tags, note_type=note_type)
                result["note"] = note
            
            # 3. 添加到数据库
            if add_to_db:
                db_success = self.add_to_database(paper_data)
                result["db_added"] = db_success
            
            result["success"] = True
            if self.noctua and self.noctua.enabled:
                print(f"\n[Noctua] {self.noctua.get_completion_message()}: {paper_data.file_name}")
            else:
                print(f"\n[完成] 论文处理完成: {paper_data.file_name}")
            
        except Exception as e:
            result["error"] = str(e)
            if self.noctua and self.noctua.enabled:
                self.noctua.print_error("general", str(e))
            else:
                print(f"\n[失败] 论文处理失败: {e}")
        
        return result
    
    def ask(
        self,
        question: str,
        paper_id: Optional[str] = None,
        top_k: int = None,
        require_citation: bool = True,
        verify: bool = False
    ) -> Dict[str, Any]:
        """
        问答功能 - 增强版
        
        Args:
            question: 问题
            paper_id: 指定论文ID（可选）
            top_k: 检索数量
            require_citation: 是否要求引用
            verify: 是否进行答案验证
            
        Returns:
            答案数据
        """
        top_k = top_k or self.config.top_k_retrieval

        if self.noctua and self.noctua.enabled:
            print(f"[Noctua] 问题: {question}")
            self.noctua.print_thinking()
        else:
            print(f"问题: {question}")

        if verify:
            answer = self.qa_system.ask_with_verification(
                question=question,
                paper_id=paper_id,
                top_k=top_k
            )
        else:
            answer = self.qa_system.ask(
                question=question,
                paper_id=paper_id,
                top_k=top_k,
                require_citation=require_citation
            )
        
        return {
            "answer": answer.content,
            "confidence": answer.confidence,
            "is_answerable": answer.is_answerable,
            "citations": answer.citations
        }
    
    def ask_complex(self, question: str, paper_id: Optional[str] = None) -> Dict[str, Any]:
        """
        复杂问题问答（多跳推理）
        
        Args:
            question: 复杂问题
            paper_id: 指定论文ID
            
        Returns:
            答案数据
        """
        print(f"复杂问题: {question}")
        return self.multi_hop_qa.answer(question, paper_id=paper_id)
    
    def explain_concept(
        self,
        concept: str,
        paper_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        解释论文中的概念
        
        Args:
            concept: 概念名称
            paper_id: 指定论文ID
            
        Returns:
            解释内容
        """
        question = f"请详细解释'{concept}'这个概念，包括定义、原理和应用。"
        return self.ask(question, paper_id=paper_id, top_k=3)
    
    def summarize_section(
        self,
        section_type: str,
        paper_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        总结特定章节
        
        Args:
            section_type: 章节类型（method/results/conclusion等）
            paper_id: 指定论文ID
            
        Returns:
            章节总结
        """
        question = f"请总结论文的{section_type}部分的主要内容。"
        return self.ask(question, paper_id=paper_id, top_k=5)
    
    def list_papers(self) -> List[Dict[str, str]]:
        """
        列出数据库中的所有论文
        
        Returns:
            论文列表
        """
        return self.vector_store.list_papers()
    
    def list_notes(
        self,
        tags: List[str] = None,
        note_type: NoteType = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有笔记
        
        Args:
            tags: 按标签筛选
            note_type: 按类型筛选
            
        Returns:
            笔记列表
        """
        return self.note_manager.list_notes(tags=tags, note_type=note_type)
    
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        获取笔记详情
        
        Args:
            note_id: 笔记ID
            
        Returns:
            笔记数据
        """
        note = self.note_manager.get_note(note_id)
        return note.to_dict() if note else None
    
    def export_note(self, note_id: str, format: str = "markdown") -> str:
        """
        导出笔记
        
        Args:
            note_id: 笔记ID
            format: 导出格式
            
        Returns:
            导出的内容
        """
        return self.note_manager.export_note(note_id, format=format)
    
    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索笔记
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的笔记列表
        """
        return self.note_manager.search_notes(query)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        db_stats = self.vector_store.get_stats()
        notes = self.note_manager.list_notes()
        papers = self.list_papers()
        
        return {
            "database": db_stats,
            "total_notes": len(notes),
            "total_papers": len(papers),
            "papers_dir": self.config.papers_dir,
            "notes_dir": self.config.notes_dir,
            "database_dir": self.config.database_dir
        }


def create_agent(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
    papers_dir: str = "./papers",
    notes_dir: str = "./notes",
    database_dir: str = "./database",
    noctua_enabled: bool = True
) -> PaperAgent:
    """
    创建论文智能体的便捷函数
    
    Args:
        api_key: OpenAI API密钥
        base_url: API基础URL
        model: 模型名称
        papers_dir: 论文存放目录
        notes_dir: 笔记存放目录
        database_dir: 数据库目录
        noctua_enabled: 是否启用 Noctua 个性化
        
    Returns:
        PaperAgent实例
    """
    config = AgentConfig(
        api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=model,
        papers_dir=papers_dir,
        notes_dir=notes_dir,
        database_dir=database_dir
    )
    
    # 创建 Noctua 个性化实例
    noctua = create_noctua(enabled=noctua_enabled) if noctua_enabled else None
    
    return PaperAgent(config, noctua=noctua)
