"""
向量数据库模块 - 负责存储和检索论文的向量表示
使用ChromaDB作为轻量级向量数据库
"""

import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentChunk:
    """文档分块数据结构"""
    id: str
    text: str
    paper_id: str
    paper_title: str
    page_number: int
    section_type: str
    metadata: Dict[str, Any]


class TextChunker:
    """文本分块器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def chunk_text(
        self,
        text: str,
        paper_id: str,
        paper_title: str,
        page_number: int = 0,
        section_type: str = "unknown"
    ) -> List[DocumentChunk]:
        """
        将文本分块
        
        Args:
            text: 原始文本
            paper_id: 论文ID
            paper_title: 论文标题
            page_number: 页码
            section_type: 章节类型
            
        Returns:
            文档块列表
        """
        chunks = []
        
        # 简单的滑动窗口分块
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 尝试在分隔符处断开
            if end < len(text):
                for sep in self.separators:
                    pos = text.rfind(sep, start, end)
                    if pos > start + self.chunk_size // 2:
                        end = pos + len(sep)
                        break
            
            chunk_text = text[start:end].strip()
            if len(chunk_text) > 50:  # 过滤太短的块
                chunk_id = hashlib.md5(
                    f"{paper_id}_{chunk_index}_{chunk_text[:50]}".encode()
                ).hexdigest()[:16]
                
                chunks.append(DocumentChunk(
                    id=chunk_id,
                    text=chunk_text,
                    paper_id=paper_id,
                    paper_title=paper_title,
                    page_number=page_number,
                    section_type=section_type,
                    metadata={
                        "chunk_index": chunk_index,
                        "start_char": start,
                        "end_char": end
                    }
                ))
                chunk_index += 1
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def chunk_paper(self, paper_data: Dict[str, Any]) -> List[DocumentChunk]:
        """
        对整个论文进行分块
        
        Args:
            paper_data: 论文解析数据
            
        Returns:
            文档块列表
        """
        all_chunks = []
        paper_id = hashlib.md5(
            paper_data.get("file_path", "").encode()
        ).hexdigest()[:12]
        paper_title = paper_data.get("file_name", "Unknown")
        
        # 按页分块
        pages = paper_data.get("pages", [])
        for page in pages:
            page_num = page.get("page_number", 0)
            text = page.get("text", "")
            
            chunks = self.chunk_text(
                text=text,
                paper_id=paper_id,
                paper_title=paper_title,
                page_number=page_num,
                section_type="page"
            )
            all_chunks.extend(chunks)
        
        # 按章节分块（如果有章节信息）
        sections = paper_data.get("sections", [])
        for section in sections:
            section_type = section.section_type if hasattr(section, 'section_type') else 'unknown'
            # 将枚举类型转换为字符串
            if hasattr(section_type, 'value'):
                section_type = section_type.value
            elif not isinstance(section_type, str):
                section_type = str(section_type)
            
            section_title = section.title if hasattr(section, 'title') else 'Unknown'
            content = section.content if hasattr(section, 'content') else str(section)
            page_num = section.page_number if hasattr(section, 'page_number') else 0
            
            chunks = self.chunk_text(
                text=content,
                paper_id=paper_id,
                paper_title=paper_title,
                page_number=page_num,
                section_type=section_type
            )
            all_chunks.extend(chunks)
        
        return all_chunks


class VectorStore:
    """向量数据库基类"""
    
    def __init__(self, collection_name: str = "papers"):
        self.collection_name = collection_name
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """添加文档到向量库"""
        raise NotImplementedError
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        raise NotImplementedError
    
    def delete_paper(self, paper_id: str) -> bool:
        """删除论文的所有文档"""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    """基于ChromaDB的向量存储"""
    
    def __init__(
        self,
        collection_name: str = "papers",
        persist_directory: str = "./database/chroma",
        embedding_model: str = "default"
    ):
        super().__init__(collection_name)
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model
        
        self.client = None
        self.collection = None
        self.embedding_function = None
        
        self._init_store()
    
    def _init_store(self):
        """初始化向量存储"""
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            
            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
            
            # 使用默认的embedding函数
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            
        except ImportError:
            raise ImportError("请安装ChromaDB: pip install chromadb")
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        添加文档块到向量库
        
        Args:
            chunks: 文档块列表
            
        Returns:
            是否添加成功
        """
        if not chunks:
            return True
        
        try:
            ids = [chunk.id for chunk in chunks]
            texts = [chunk.text for chunk in chunks]
            metadatas = [
                {
                    "paper_id": chunk.paper_id,
                    "paper_title": chunk.paper_title,
                    "page_number": chunk.page_number,
                    "section_type": chunk.section_type,
                    **chunk.metadata
                }
                for chunk in chunks
            ]
            
            # 分批添加（避免一次性添加太多）
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                end_idx = min(i + batch_size, len(chunks))
                self.collection.add(
                    ids=ids[i:end_idx],
                    documents=texts[i:end_idx],
                    metadatas=metadatas[i:end_idx]
                )
            
            return True
            
        except Exception as e:
            print(f"添加文档失败: {e}")
            return False
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            搜索结果列表
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_dict,
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化结果
            formatted_results = []
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "score": 1 - results["distances"][0][i] if results["distances"] else None
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def search_by_paper(
        self,
        query: str,
        paper_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        在指定论文内搜索
        
        Args:
            query: 查询文本
            paper_id: 论文ID
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        return self.search(query, top_k, filter_dict={"paper_id": paper_id})
    
    def delete_paper(self, paper_id: str) -> bool:
        """
        删除论文的所有文档
        
        Args:
            paper_id: 论文ID
            
        Returns:
            是否删除成功
        """
        try:
            self.collection.delete(where={"paper_id": paper_id})
            return True
        except Exception as e:
            print(f"删除论文失败: {e}")
            return False
    
    def get_paper_chunks(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        获取论文的所有文档块
        
        Args:
            paper_id: 论文ID
            
        Returns:
            文档块列表
        """
        try:
            results = self.collection.get(
                where={"paper_id": paper_id},
                include=["documents", "metadatas"]
            )
            
            chunks = []
            for i in range(len(results["ids"])):
                chunks.append({
                    "id": results["ids"][i],
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
            
            return chunks
            
        except Exception as e:
            print(f"获取论文块失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def list_papers(self) -> List[Dict[str, str]]:
        """
        列出所有论文
        
        Returns:
            论文列表
        """
        try:
            results = self.collection.get(include=["metadatas"])
            
            papers = {}
            for metadata in results["metadatas"]:
                paper_id = metadata.get("paper_id")
                paper_title = metadata.get("paper_title")
                if paper_id and paper_id not in papers:
                    papers[paper_id] = {
                        "id": paper_id,
                        "title": paper_title
                    }
            
            return list(papers.values())
            
        except Exception as e:
            print(f"获取论文列表失败: {e}")
            return []


class SimpleVectorStore(VectorStore):
    """简单的内存向量存储（用于测试）"""
    
    def __init__(self, collection_name: str = "papers"):
        super().__init__(collection_name)
        self.documents: Dict[str, DocumentChunk] = {}
        self.embeddings: Dict[str, List[float]] = {}
    
    def _simple_embedding(self, text: str) -> List[float]:
        """简单的词频嵌入（仅用于测试）"""
        # 创建一个简单的哈希嵌入
        import random
        random.seed(hash(text) % 10000)
        return [random.random() for _ in range(128)]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot_product / (norm_a * norm_b)
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """添加文档"""
        for chunk in chunks:
            self.documents[chunk.id] = chunk
            self.embeddings[chunk.id] = self._simple_embedding(chunk.text)
        return True
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档"""
        query_embedding = self._simple_embedding(query)
        
        scores = []
        for doc_id, doc in self.documents.items():
            # 应用过滤
            if filter_dict:
                match = True
                for key, value in filter_dict.items():
                    if key == "paper_id" and doc.paper_id != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 计算相似度
            similarity = self._cosine_similarity(
                query_embedding,
                self.embeddings[doc_id]
            )
            scores.append((doc_id, similarity))
        
        # 排序并返回top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in scores[:top_k]:
            doc = self.documents[doc_id]
            results.append({
                "id": doc_id,
                "text": doc.text,
                "metadata": {
                    "paper_id": doc.paper_id,
                    "paper_title": doc.paper_title,
                    "page_number": doc.page_number,
                    "section_type": doc.section_type
                },
                "score": score
            })
        
        return results
    
    def delete_paper(self, paper_id: str) -> bool:
        """删除论文"""
        ids_to_remove = [
            doc_id for doc_id, doc in self.documents.items()
            if doc.paper_id == paper_id
        ]
        for doc_id in ids_to_remove:
            del self.documents[doc_id]
            del self.embeddings[doc_id]
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_documents": len(self.documents),
            "collection_name": self.collection_name
        }


def create_vector_store(
    store_type: str = "chroma",
    **kwargs
) -> VectorStore:
    """
    创建向量存储实例
    
    Args:
        store_type: 存储类型 (chroma, simple)
        **kwargs: 其他参数
        
    Returns:
        VectorStore实例
    """
    if store_type == "chroma":
        return ChromaVectorStore(**kwargs)
    elif store_type == "simple":
        return SimpleVectorStore(**kwargs)
    else:
        raise ValueError(f"未知的存储类型: {store_type}")
