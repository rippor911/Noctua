"""
PDF解析模块 - 负责从PDF文件中提取文本内容

参考 paper-qa 的最佳实践，改进：
1. 更准确的元数据提取（DOI、作者、标题）
2. 支持表格和公式提取
3. 更智能的章节分割
4. 引用追踪
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SectionType(Enum):
    """论文章节类型"""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENT = "experiment"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    ACKNOWLEDGMENTS = "acknowledgments"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


@dataclass
class Citation:
    """引用信息"""
    citation_key: str  # 引用标识符
    authors: List[str] = field(default_factory=list)
    title: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    venue: str = ""


@dataclass
class PaperSection:
    """论文段落数据结构"""
    title: str
    content: str
    page_number: int
    section_type: SectionType
    subsections: List['PaperSection'] = field(default_factory=list)


@dataclass
class PaperMetadata:
    """论文元数据"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    venue: str = ""  # 期刊/会议名称
    citation_count: Optional[int] = None
    references: List[Citation] = field(default_factory=list)


@dataclass
class Table:
    """表格数据"""
    page_number: int
    caption: str
    content: str
    data: List[List[str]] = field(default_factory=list)


@dataclass
class Figure:
    """图片数据"""
    page_number: int
    caption: str
    description: str = ""


@dataclass
class ParsedPaper:
    """解析后的论文完整数据结构"""
    file_path: str
    file_name: str
    doc_id: str  # 文档唯一标识
    metadata: PaperMetadata
    full_text: str
    pages: List[Dict[str, Any]]
    sections: List[PaperSection]
    tables: List[Table] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    citations_map: Dict[str, Citation] = field(default_factory=dict)


class PDFParser:
    """PDF解析器基类"""

    def __init__(self):
        self.supported_extensions = ['.pdf']

    def parse(self, file_path: str) -> ParsedPaper:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径

        Returns:
            ParsedPaper对象
        """
        raise NotImplementedError


class PyMuPDFParser(PDFParser):
    """使用PyMuPDF (fitz) 解析PDF - 增强版"""

    def __init__(self):
        super().__init__()
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
        except ImportError:
            raise ImportError("请安装PyMuPDF: pip install PyMuPDF")

    def parse(self, file_path: str) -> ParsedPaper:
        """解析PDF文件并提取内容"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if file_path.suffix.lower() not in self.supported_extensions:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

        # 生成文档ID
        doc_id = self._generate_doc_id(file_path)

        doc = self.fitz.open(file_path)

        full_text = ""
        pages_text = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages_text.append({
                'page_number': page_num + 1,
                'text': text
            })
            full_text += f"\n--- Page {page_num + 1} ---\n{text}"

        doc.close()

        # 提取元数据
        metadata = self._extract_metadata(full_text)

        # 分段
        sections = self._segment_paper(full_text, pages_text)

        # 提取表格（简化版）
        tables = self._extract_tables(full_text, pages_text)

        return ParsedPaper(
            file_path=str(file_path),
            file_name=file_path.name,
            doc_id=doc_id,
            metadata=metadata,
            full_text=full_text,
            pages=pages_text,
            sections=sections,
            tables=tables
        )

    def _generate_doc_id(self, file_path: Path) -> str:
        """生成文档唯一标识"""
        content = f"{file_path.name}_{file_path.stat().st_size}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _extract_metadata(self, text: str) -> PaperMetadata:
        """从文本中提取元数据 - 增强版"""
        lines = text.split('\n')

        # 尝试提取标题（通常是前几行，长度适中）
        title = self._extract_title(lines)

        # 尝试提取作者
        authors = self._extract_authors(text)

        # 尝试提取摘要
        abstract = self._extract_abstract(text)

        # 尝试提取DOI
        doi = self._extract_doi(text)

        # 尝试提取关键词
        keywords = self._extract_keywords(text)

        return PaperMetadata(
            title=title,
            authors=authors,
            abstract=abstract,
            keywords=keywords,
            doi=doi
        )

    def _extract_title(self, lines: List[str]) -> str:
        """提取论文标题"""
        # 标题通常是前几行中长度适中的行
        for line in lines[:20]:
            line = line.strip()
            # 标题特征：长度20-200，不是全大写，不包含常见非标题词汇
            if (20 <= len(line) <= 200 and
                not line.isupper() and
                not any(word in line.lower() for word in ['abstract', 'introduction', 'keywords', 'author', 'university', 'institute'])):
                return line
        return ""

    def _extract_authors(self, text: str) -> List[str]:
        """提取作者列表"""
        authors = []

        # 常见的作者行模式
        author_patterns = [
            r'(?:Authors?|作者)[:\s]+(.+?)(?:\n|$)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)+)',  # 多个作者
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)*)',  # 逗号分隔
        ]

        for pattern in author_patterns:
            match = re.search(pattern, text[:2000], re.MULTILINE)
            if match:
                author_text = match.group(1)
                # 分割多个作者
                author_list = re.split(r',\s*and\s*|,\s*|\s+and\s+', author_text)
                authors = [a.strip() for a in author_list if len(a.strip()) > 2]
                break

        return authors[:10]  # 最多10个作者

    def _extract_abstract(self, text: str) -> str:
        """提取摘要"""
        abstract_patterns = [
            (r'Abstract[\s:]*(.+?)(?=\n\s*\n|\n\s*(?:1\.|I\.|Introduction|Keywords))', 'en'),
            (r'摘要[\s:]*(.+?)(?=\n\s*\n|\n\s*(?:1\.|一、|引言|关键词))', 'zh'),
        ]

        for pattern, lang in abstract_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # 清理摘要文本
                abstract = re.sub(r'\s+', ' ', abstract)
                return abstract

        return ""

    def _extract_doi(self, text: str) -> Optional[str]:
        """提取DOI"""
        doi_patterns = [
            r'10\.\d{4,}/[^\s]+',
            r'DOI[:\s]+(10\.\d{4,}/[^\s]+)',
            r'doi\.org/(10\.\d{4,}/[^\s]+)',
        ]

        for pattern in doi_patterns:
            match = re.search(pattern, text)
            if match:
                doi = match.group(1) if '(' in pattern else match.group(0)
                return doi.strip()

        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keyword_patterns = [
            r'Keywords?[:\s]+(.+?)(?=\n|$)',
            r'关键词[:\s]+(.+?)(?=\n|$)',
        ]

        for pattern in keyword_patterns:
            match = re.search(pattern, text[:5000], re.IGNORECASE)
            if match:
                keywords_text = match.group(1)
                # 分割关键词
                keywords = [k.strip() for k in re.split(r'[,;；，]', keywords_text)]
                return [k for k in keywords if len(k) > 1 and len(k) < 50]

        return []

    def _segment_paper(self, full_text: str, pages_text: List[Dict]) -> List[PaperSection]:
        """将论文分段 - 增强版"""
        sections = []

        # 更全面的章节标题模式
        section_patterns = [
            (r'(?i)^\s*(?:1|I)\.?\s*Introduction\s*$', SectionType.INTRODUCTION),
            (r'(?i)^\s*(?:2|II)\.?\s*Related\s+Work\s*$', SectionType.RELATED_WORK),
            (r'(?i)^\s*(?:3|III)\.?\s*(?:Method|Methodology|Methods|Approach)\s*$', SectionType.METHOD),
            (r'(?i)^\s*(?:4|IV)\.?\s*(?:Experiments?|Experimental\s+Setup|Evaluation)\s*$', SectionType.EXPERIMENT),
            (r'(?i)^\s*(?:5|V)\.?\s*Results?(?:\s+and\s+Discussion)?\s*$', SectionType.RESULTS),
            (r'(?i)^\s*(?:6|VI)\.?\s*Discussion\s*$', SectionType.DISCUSSION),
            (r'(?i)^\s*(?:7|VII)\.?\s*Conclusion(?:s)?\s*$', SectionType.CONCLUSION),
            (r'(?i)^\s*Abstract\s*$', SectionType.ABSTRACT),
            (r'(?i)^\s*References?(?:\s+and\s+Notes?)?\s*$', SectionType.REFERENCES),
            (r'(?i)^\s*Acknowledgments?\s*$', SectionType.ACKNOWLEDGMENTS),
            (r'(?i)^\s*Appendix(?:es)?\s*$', SectionType.APPENDIX),
        ]

        lines = full_text.split('\n')
        current_section = None
        current_content = []
        current_page = 1
        current_type = SectionType.UNKNOWN

        for i, line in enumerate(lines):
            # 检测页面标记
            page_match = re.match(r'^--- Page (\d+) ---$', line)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            # 检测章节标题
            is_section_header = False
            for pattern, section_type in section_patterns:
                if re.match(pattern, line.strip()):
                    # 保存之前的章节
                    if current_section:
                        sections.append(PaperSection(
                            title=current_section,
                            content='\n'.join(current_content).strip(),
                            page_number=current_page,
                            section_type=current_type
                        ))

                    current_section = line.strip()
                    current_content = []
                    current_type = section_type
                    is_section_header = True
                    break

            if not is_section_header and current_section:
                current_content.append(line)

        # 保存最后一个章节
        if current_section and current_content:
            sections.append(PaperSection(
                title=current_section,
                content='\n'.join(current_content).strip(),
                page_number=current_page,
                section_type=current_type
            ))

        return sections

    def _extract_tables(self, full_text: str, pages_text: List[Dict]) -> List[Table]:
        """提取表格信息（简化版）"""
        tables = []

        # 表格标题模式
        table_patterns = [
            r'Table\s+(\d+)[:.]?\s*(.+?)(?=\n|$)',
            r'TABLE\s+(\d+)[:.]?\s*(.+?)(?=\n|$)',
        ]

        for page in pages_text:
            page_num = page['page_number']
            text = page['text']

            for pattern in table_patterns:
                for match in re.finditer(pattern, text):
                    table_num = match.group(1)
                    caption = match.group(2).strip()

                    tables.append(Table(
                        page_number=page_num,
                        caption=f"Table {table_num}: {caption}",
                        content=""
                    ))

        return tables


class SimplePDFParser(PDFParser):
    """简单的PDF解析器，使用pdfplumber作为备选"""

    def __init__(self):
        super().__init__()
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
        except ImportError:
            raise ImportError("请安装pdfplumber: pip install pdfplumber")

    def parse(self, file_path: str) -> ParsedPaper:
        """解析PDF文件"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 生成文档ID
        doc_id = hashlib.md5(f"{file_path.name}_{file_path.stat().st_size}".encode()).hexdigest()[:12]

        full_text = ""
        pages_text = []

        with self.pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages_text.append({
                    'page_number': i + 1,
                    'text': text
                })
                full_text += f"\n--- Page {i + 1} ---\n{text}"

        return ParsedPaper(
            file_path=str(file_path),
            file_name=file_path.name,
            doc_id=doc_id,
            metadata=PaperMetadata(),
            full_text=full_text,
            pages=pages_text,
            sections=[]
        )


def get_parser(parser_type: str = "pymupdf") -> PDFParser:
    """
    获取PDF解析器实例

    Args:
        parser_type: 解析器类型，可选 "pymupdf" 或 "pdfplumber"

    Returns:
        PDFParser实例
    """
    if parser_type == "pymupdf":
        return PyMuPDFParser()
    elif parser_type == "pdfplumber":
        return SimplePDFParser()
    else:
        raise ValueError(f"未知的解析器类型: {parser_type}")
