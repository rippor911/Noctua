"""
笔记管理模块 - 负责生成、存储和管理论文笔记

参考 paper-qa 和 mad-professor 的最佳实践，改进：
1. 更全面的笔记结构（方法、实验、结果分离）
2. 支持引用追踪
3. 更好的Markdown导出格式
4. 学术引用格式支持
5. 友好的文件名（使用论文标题）
6. 同时保存JSON和Markdown格式
"""

import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum


class NoteType(Enum):
    """笔记类型"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    METHOD = "method"
    RESULTS = "results"
    CRITICAL = "critical"


@dataclass
class SectionNote:
    """章节笔记"""
    name: str
    type: str
    summary: str
    key_points: List[str]
    citations: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Note:
    """笔记数据结构 - 增强版"""
    id: str
    paper_id: str
    paper_title: str
    paper_doi: Optional[str]
    paper_authors: List[str]
    created_at: str
    updated_at: str
    
    # 核心内容
    summary: str
    key_points: List[str]
    sections: List[SectionNote]
    
    # 详细分析
    methodology: str
    experiments: str
    results: str
    conclusions: str
    limitations: str
    
    # 元数据
    tags: List[str]
    note_type: NoteType
    citations: List[Dict[str, str]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['note_type'] = self.note_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """从字典创建"""
        data = data.copy()
        data['note_type'] = NoteType(data.get('note_type', 'detailed'))
        
        # 转换章节笔记
        if 'sections' in data:
            data['sections'] = [
                SectionNote(**s) if isinstance(s, dict) else s
                for s in data['sections']
            ]
        
        return cls(**data)


class NoteManager:
    """笔记管理器 - 增强版"""
    
    def __init__(self, notes_dir: str = "./notes"):
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.notes_dir / "index.json"
        self.notes_index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """加载笔记索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"notes": [], "papers": {}}
    
    def _save_index(self):
        """保存笔记索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.notes_index, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, content: str) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().isoformat()
        content_hash = hashlib.md5(f"{content}{timestamp}".encode()).hexdigest()[:8]
        return f"note_{content_hash}"

    def _generate_paper_id(self, file_path: str) -> str:
        """生成论文ID"""
        return hashlib.md5(file_path.encode()).hexdigest()[:12]

    def _sanitize_filename(self, title: str, max_length: int = 80) -> str:
        """
        将论文标题转换为安全的文件名

        - 移除或替换特殊字符
        - 限制长度
        - 保留可读性
        """
        if not title:
            return "untitled"

        # 替换特殊字符为下划线
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', title)

        # 替换空白字符为单个下划线
        sanitized = re.sub(r'\s+', '_', sanitized)

        # 移除连续的下划线
        sanitized = re.sub(r'_+', '_', sanitized)

        # 移除首尾的点和下划线
        sanitized = sanitized.strip('._')

        # 限制长度（保留最后一部分以便识别）
        if len(sanitized) > max_length:
            # 尝试在单词边界截断
            truncated = sanitized[:max_length]
            last_underscore = truncated.rfind('_')
            if last_underscore > max_length * 0.5:  # 如果能在后半部分找到下划线
                sanitized = truncated[:last_underscore]
            else:
                sanitized = truncated

        # 确保不为空
        if not sanitized:
            sanitized = "paper"

        return sanitized
    
    def create_note(
        self,
        paper_path: str,
        paper_title: str,
        paper_doi: Optional[str] = None,
        paper_authors: List[str] = None,
        summary: str = "",
        key_points: List[str] = None,
        sections: List[Dict[str, Any]] = None,
        methodology: str = "",
        experiments: str = "",
        results: str = "",
        conclusions: str = "",
        limitations: str = "",
        tags: List[str] = None,
        note_type: NoteType = NoteType.DETAILED
    ) -> Note:
        """
        创建新笔记 - 增强版
        
        Args:
            paper_path: 论文文件路径
            paper_title: 论文标题
            paper_doi: DOI
            paper_authors: 作者列表
            summary: 摘要
            key_points: 关键要点
            sections: 章节分析
            methodology: 研究方法
            experiments: 实验设计
            results: 实验结果
            conclusions: 结论
            limitations: 局限性
            tags: 标签列表
            note_type: 笔记类型
            
        Returns:
            Note对象
        """
        paper_id = self._generate_paper_id(paper_path)
        note_id = self._generate_id(paper_path + paper_title)
        
        now = datetime.now().isoformat()
        
        # 转换章节数据
        section_notes = []
        if sections:
            for s in sections:
                if isinstance(s, dict):
                    section_notes.append(SectionNote(
                        name=s.get('name', 'Unknown'),
                        type=s.get('type', 'unknown'),
                        summary=s.get('summary', ''),
                        key_points=s.get('key_points', []),
                        citations=s.get('citations', [])
                    ))
        
        note = Note(
            id=note_id,
            paper_id=paper_id,
            paper_title=paper_title,
            paper_doi=paper_doi,
            paper_authors=paper_authors or [],
            created_at=now,
            updated_at=now,
            summary=summary,
            key_points=key_points or [],
            sections=section_notes,
            methodology=methodology,
            experiments=experiments,
            results=results,
            conclusions=conclusions,
            limitations=limitations,
            tags=tags or [],
            note_type=note_type,
            citations=[]
        )

        # 生成友好的文件名（基于论文标题）
        friendly_name = self._sanitize_filename(paper_title)

        # 检查是否有重名文件，如果有则添加序号
        base_name = friendly_name
        counter = 1
        while (self.notes_dir / f"{friendly_name}.md").exists() or \
              (self.notes_dir / f"{friendly_name}.json").exists():
            friendly_name = f"{base_name}_{counter}"
            counter += 1

        # 保存JSON格式（用于程序读取）
        json_file = self.notes_dir / f"{friendly_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(note.to_dict(), f, ensure_ascii=False, indent=2)

        # 保存Markdown格式（供用户阅读）
        md_file = self.notes_dir / f"{friendly_name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self._export_to_markdown(note))

        # 更新索引（包含文件名信息）
        self.notes_index["notes"].append({
            "id": note_id,
            "paper_id": paper_id,
            "paper_title": paper_title,
            "paper_doi": paper_doi,
            "created_at": now,
            "tags": tags or [],
            "note_type": note_type.value,
            "filename": friendly_name,
            "json_file": f"{friendly_name}.json",
            "md_file": f"{friendly_name}.md"
        })
        self.notes_index["papers"][paper_id] = {
            "path": paper_path,
            "title": paper_title,
            "doi": paper_doi,
            "note_id": note_id,
            "filename": friendly_name
        }
        self._save_index()

        return note
    
    def get_note(self, note_id: str) -> Optional[Note]:
        """获取笔记（支持note_id或文件名）"""
        # 首先尝试直接查找（旧格式兼容）
        note_file = self.notes_dir / f"{note_id}.json"
        if note_file.exists():
            with open(note_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Note.from_dict(data)

        # 从索引中查找文件名
        for note_info in self.notes_index["notes"]:
            if note_info["id"] == note_id:
                filename = note_info.get("filename", note_id)
                note_file = self.notes_dir / f"{filename}.json"
                if note_file.exists():
                    with open(note_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return Note.from_dict(data)
                break

        return None

    def get_note_by_filename(self, filename: str) -> Optional[Note]:
        """通过文件名获取笔记（不需要扩展名）"""
        # 去除扩展名（如果用户提供了）
        filename = filename.replace('.json', '').replace('.md', '')

        note_file = self.notes_dir / f"{filename}.json"
        if note_file.exists():
            with open(note_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Note.from_dict(data)

        return None
    
    def get_note_by_paper(self, paper_path: str) -> Optional[Note]:
        """通过论文路径获取笔记"""
        paper_id = self._generate_paper_id(paper_path)
        paper_info = self.notes_index["papers"].get(paper_id)
        
        if paper_info:
            return self.get_note(paper_info["note_id"])
        return None
    
    def update_note(self, note_id: str, updates: Dict[str, Any]) -> Optional[Note]:
        """更新笔记"""
        note = self.get_note(note_id)
        if not note:
            return None
        
        # 更新字段
        note_dict = note.to_dict()
        for key, value in updates.items():
            if key in note_dict and key != 'id':
                note_dict[key] = value
        
        note_dict["updated_at"] = datetime.now().isoformat()
        
        # 保存
        note_file = self.notes_dir / f"{note_id}.json"
        with open(note_file, 'w', encoding='utf-8') as f:
            json.dump(note_dict, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        for note_info in self.notes_index["notes"]:
            if note_info["id"] == note_id:
                note_info["updated_at"] = note_dict["updated_at"]
                if "tags" in updates:
                    note_info["tags"] = updates["tags"]
                break
        self._save_index()
        
        return Note.from_dict(note_dict)
    
    def delete_note(self, note_id: str) -> bool:
        """删除笔记（同时删除JSON和Markdown文件）"""
        # 从索引中查找文件名
        filename = None
        for note_info in self.notes_index["notes"]:
            if note_info["id"] == note_id:
                filename = note_info.get("filename")
                break

        # 如果没有找到索引，尝试直接使用note_id
        if not filename:
            filename = note_id

        # 删除JSON文件
        json_file = self.notes_dir / f"{filename}.json"
        if json_file.exists():
            json_file.unlink()

        # 删除Markdown文件
        md_file = self.notes_dir / f"{filename}.md"
        if md_file.exists():
            md_file.unlink()

        # 如果文件都不存在，返回False
        if not json_file.exists() and not md_file.exists():
            # 尝试旧格式（直接删除）
            old_file = self.notes_dir / f"{note_id}.json"
            if old_file.exists():
                old_file.unlink()
            else:
                return False

        # 更新索引
        self.notes_index["notes"] = [
            n for n in self.notes_index["notes"] if n["id"] != note_id
        ]

        papers_to_remove = [
            pid for pid, info in self.notes_index["papers"].items()
            if info.get("note_id") == note_id
        ]
        for pid in papers_to_remove:
            del self.notes_index["papers"][pid]

        self._save_index()
        return True

    def list_notes(self, tags: List[str] = None, note_type: NoteType = None) -> List[Dict[str, Any]]:
        """列出笔记"""
        notes = self.notes_index["notes"]

        if tags:
            notes = [
                n for n in notes
                if any(tag in n.get("tags", []) for tag in tags)
            ]

        if note_type:
            notes = [
                n for n in notes
                if n.get("note_type") == note_type.value
            ]

        return sorted(notes, key=lambda x: x["created_at"], reverse=True)

    def list_papers_summary(self) -> List[Dict[str, Any]]:
        """
        列出所有已读论文的摘要信息（方便用户查看）

        Returns:
            包含论文标题、文件名、创建时间等信息的列表
        """
        papers = []
        for paper_id, paper_info in self.notes_index["papers"].items():
            note_info = None
            for note in self.notes_index["notes"]:
                if note["paper_id"] == paper_id:
                    note_info = note
                    break

            if note_info:
                papers.append({
                    "paper_id": paper_id,
                    "title": paper_info.get("title", "Unknown"),
                    "filename": note_info.get("filename", "unknown"),
                    "md_file": note_info.get("md_file", ""),
                    "json_file": note_info.get("json_file", ""),
                    "created_at": note_info.get("created_at", ""),
                    "tags": note_info.get("tags", []),
                    "doi": paper_info.get("doi")
                })

        return sorted(papers, key=lambda x: x["created_at"], reverse=True)

    def get_reading_list(self) -> str:
        """
        生成可读的已读论文列表（Markdown格式）

        Returns:
            Markdown格式的论文列表
        """
        papers = self.list_papers_summary()

        if not papers:
            return "# 📚 已读论文列表\n\n还没有读过任何论文呢~"

        md = "# 📚 已读论文列表\n\n"
        md += f"共 **{len(papers)}** 篇论文\n\n"
        md += "---\n\n"

        for i, paper in enumerate(papers, 1):
            md += f"## {i}. {paper['title']}\n\n"
            md += f"- **文件名**: `{paper['md_file']}`\n"
            md += f"- **阅读时间**: {paper['created_at'][:10]}\n"
            if paper['tags']:
                md += f"- **标签**: {', '.join(paper['tags'])}\n"
            if paper['doi']:
                md += f"- **DOI**: {paper['doi']}\n"
            md += "\n"

        md += "---\n\n"
        md += "💡 **提示**: 使用 `list` 命令可以查看此列表，或者直接查看 `notes/` 目录下的 `.md` 文件。\n"

        return md
    
    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """搜索笔记"""
        results = []
        query_lower = query.lower()
        
        for note_info in self.notes_index["notes"]:
            note = self.get_note(note_info["id"])
            if not note:
                continue
            
            searchable = f"{note.paper_title} {note.summary} {' '.join(note.key_points)}"
            if query_lower in searchable.lower():
                results.append({
                    "id": note.id,
                    "paper_title": note.paper_title,
                    "summary": note.summary[:200] + "..." if len(note.summary) > 200 else note.summary,
                    "tags": note.tags,
                    "created_at": note.created_at
                })
        
        return results
    
    def export_note(self, note_id: str, format: str = "markdown") -> str:
        """
        导出笔记 - 增强版Markdown格式
        
        Args:
            note_id: 笔记ID
            format: 导出格式 (markdown, json)
            
        Returns:
            导出的内容
        """
        note = self.get_note(note_id)
        if not note:
            return ""
        
        if format == "json":
            return json.dumps(note.to_dict(), ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            return self._export_to_markdown(note)
        
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def _export_to_markdown(self, note: Note) -> str:
        """导出为Markdown格式"""
        md = f"""# {note.paper_title}

"""
        
        # 元数据
        if note.paper_authors:
            md += f"**作者:** {', '.join(note.paper_authors)}\n\n"
        if note.paper_doi:
            md += f"**DOI:** {note.paper_doi}\n\n"
        
        md += f"**笔记类型:** {note.note_type.value}\n\n"
        
        if note.tags:
            md += f"**标签:** {', '.join(note.tags)}\n\n"
        
        md += "---\n\n"
        
        # 摘要
        md += f"""## 摘要

{note.summary}

"""
        
        # 关键要点
        if note.key_points:
            md += "## 关键要点\n\n"
            for i, point in enumerate(note.key_points, 1):
                md += f"{i}. {point}\n"
            md += "\n"
        
        # 研究方法
        if note.methodology:
            md += f"""## 研究方法

{note.methodology}

"""
        
        # 实验设计
        if note.experiments:
            md += f"""## 实验设计

{note.experiments}

"""
        
        # 实验结果
        if note.results:
            md += f"""## 实验结果

{note.results}

"""
        
        # 结论
        if note.conclusions:
            md += f"""## 结论

{note.conclusions}

"""
        
        # 局限性
        if note.limitations:
            md += f"""## 局限性与未来工作

{note.limitations}

"""
        
        # 章节详细分析
        if note.sections:
            md += """## 章节分析

"""
            for section in note.sections:
                md += f"### {section.name}\n\n"
                md += f"{section.summary}\n\n"
                
                if section.key_points:
                    md += "**要点:**\n"
                    for point in section.key_points:
                        md += f"- {point}\n"
                    md += "\n"
        
        # 页脚
        md += f"""---

*创建于: {note.created_at}*  
*更新于: {note.updated_at}*
"""
        
        return md


class NoteGenerator:
    """笔记生成器 - 使用LLM生成笔记内容"""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate_from_paper(self, paper_data: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """
        从论文数据生成笔记 - 增强版（支持进度回调）

        Args:
            paper_data: 论文解析数据
            progress_callback: 进度回调函数，接收进度值(0-1)和步骤描述

        Returns:
            笔记内容字典
        """
        full_text = paper_data.get('full_text', '')
        sections = paper_data.get('sections', [])
        metadata = paper_data.get('metadata', {})

        def update_progress(progress: float, step: str):
            if progress_callback:
                progress_callback(progress, step)

        # 步骤1: 生成摘要 (0% - 25%)
        update_progress(0.0, "正在阅读摘要...")
        summary = self.llm_client.generate_summary(full_text[:10000])
        update_progress(0.25, "摘要生成完成")

        # 步骤2: 提取关键要点 (25% - 50%)
        update_progress(0.25, "正在提取关键要点...")
        key_points = self.llm_client.extract_key_points(full_text[:10000])
        update_progress(0.50, "关键要点提取完成")

        # 步骤3: 分析论文结构 (50% - 80%)
        update_progress(0.50, "正在分析论文结构...")
        structure_analysis = self.llm_client.analyze_paper_structure(full_text[:15000])
        update_progress(0.80, "结构分析完成")

        # 步骤4: 提取章节信息 (80% - 100%)
        update_progress(0.80, "正在整理章节信息...")

        # 提取章节信息
        sections_info = []
        if isinstance(structure_analysis, dict) and "sections" in structure_analysis:
            sections_info = structure_analysis["sections"]

        # 提取各部分
        methodology = structure_analysis.get("methodology", "") if isinstance(structure_analysis, dict) else ""
        conclusions = structure_analysis.get("conclusion", "") if isinstance(structure_analysis, dict) else ""

        # 尝试提取实验和结果（从章节中）
        experiments = ""
        results = ""
        limitations = ""

        for section in sections_info:
            section_type = section.get('type', '').lower()
            section_summary = section.get('summary', '')

            if 'experiment' in section_type or 'experimental' in section_type:
                experiments = section_summary
            elif 'result' in section_type:
                results = section_summary
            elif 'limitation' in section_type or 'future' in section_type:
                limitations = section_summary

        update_progress(1.0, "笔记生成完成！")

        return {
            "summary": summary,
            "key_points": key_points,
            "sections": sections_info,
            "methodology": methodology,
            "experiments": experiments,
            "results": results,
            "conclusions": conclusions,
            "limitations": limitations
        }
