"""
问答系统模块 - 实现无幻觉的论文问答功能
核心策略：
1. 基于检索增强生成（RAG）
2. 严格限制回答范围在提供的上下文中
3. 标注引用来源
4. 不确定时明确说明
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class Answer:
    """答案数据结构"""
    content: str
    citations: List[Dict[str, Any]]  # 引用来源
    confidence: str  # high, medium, low
    is_answerable: bool  # 是否能基于上下文回答
    context_used: List[str]  # 使用的上下文片段


@dataclass
class RetrievedContext:
    """检索到的上下文"""
    text: str
    paper_title: str
    page_number: int
    section_type: str
    score: float
    paper_id: str


class ContextRetriever:
    """上下文检索器"""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
    
    def retrieve(
        self,
        query: str,
        paper_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[RetrievedContext]:
        """
        检索相关上下文
        
        Args:
            query: 查询问题
            paper_id: 指定论文ID（可选）
            top_k: 返回结果数量
            min_score: 最小相似度分数
            
        Returns:
            检索到的上下文列表
        """
        # 构建过滤条件
        filter_dict = {"paper_id": paper_id} if paper_id else None
        
        # 搜索向量库
        results = self.vector_store.search(query, top_k=top_k * 2, filter_dict=filter_dict)
        
        contexts = []
        for result in results:
            score = result.get("score", 0)
            if score < min_score:
                continue
            
            metadata = result.get("metadata", {})
            contexts.append(RetrievedContext(
                text=result.get("text", ""),
                paper_title=metadata.get("paper_title", "Unknown"),
                page_number=metadata.get("page_number", 0),
                section_type=metadata.get("section_type", "unknown"),
                score=score,
                paper_id=metadata.get("paper_id", "")
            ))
        
        # 按分数排序并返回top_k
        contexts.sort(key=lambda x: x.score, reverse=True)
        return contexts[:top_k]
    
    def retrieve_multi_paper(
        self,
        query: str,
        paper_ids: List[str],
        top_k_per_paper: int = 3
    ) -> Dict[str, List[RetrievedContext]]:
        """
        从多篇论文中检索上下文
        
        Args:
            query: 查询问题
            paper_ids: 论文ID列表
            top_k_per_paper: 每篇论文返回的结果数
            
        Returns:
            按论文ID分组的上下文
        """
        results = {}
        for paper_id in paper_ids:
            contexts = self.retrieve(query, paper_id=paper_id, top_k=top_k_per_paper)
            if contexts:
                results[paper_id] = contexts
        return results


class HallucinationDetector:
    """幻觉检测器"""
    
    # 不确定表达的标记词
    UNCERTAINTY_MARKERS = [
        "可能", "也许", "大概", "似乎", "应该", "或许",
        "might", "maybe", "perhaps", "possibly", "probably",
        "likely", "seems", "appears", "could be"
    ]
    
    # 外部知识的标记词
    EXTERNAL_KNOWLEDGE_MARKERS = [
        "根据一般知识", "众所周知", "通常", "一般来说",
        "according to general knowledge", "it is well known",
        "generally", "typically", "in general"
    ]
    
    @classmethod
    def check_answer(cls, answer: str, contexts: List[str]) -> Dict[str, Any]:
        """
        检查答案是否存在幻觉
        
        Args:
            answer: 生成的答案
            contexts: 使用的上下文
            
        Returns:
            检测结果
        """
        issues = []
        confidence = "high"
        
        # 检查不确定表达
        uncertainty_count = 0
        for marker in cls.UNCERTAINTY_MARKERS:
            if marker.lower() in answer.lower():
                uncertainty_count += 1
        
        if uncertainty_count >= 2:
            issues.append(f"发现{uncertainty_count}处不确定表达")
            confidence = "medium"
        
        # 检查外部知识标记
        for marker in cls.EXTERNAL_KNOWLEDGE_MARKERS:
            if marker.lower() in answer.lower():
                issues.append(f"可能包含外部知识: '{marker}'")
                confidence = "low"
        
        # 检查是否有具体的事实支撑
        combined_context = " ".join(contexts).lower()
        answer_words = set(re.findall(r'\b\w+\b', answer.lower()))
        context_words = set(re.findall(r'\b\w+\b', combined_context))
        
        # 计算关键信息覆盖率
        if len(answer_words) > 0:
            coverage = len(answer_words & context_words) / len(answer_words)
            if coverage < 0.3:
                issues.append("答案与上下文关联度较低")
                confidence = "low"
        
        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "confidence": confidence,
            "suggestion": "建议重新检查答案的事实依据" if issues else None
        }


class QASystem:
    """问答系统 - 核心类"""
    
    def __init__(self, llm_client, vector_store):
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.retriever = ContextRetriever(vector_store)
    
    def ask(
        self,
        question: str,
        paper_id: Optional[str] = None,
        top_k: int = 5,
        require_citation: bool = True
    ) -> Answer:
        """
        回答问题
        
        Args:
            question: 问题
            paper_id: 指定论文ID（可选）
            top_k: 检索的上下文数量
            require_citation: 是否要求标注引用
            
        Returns:
            Answer对象
        """
        # 1. 检索相关上下文
        contexts = self.retriever.retrieve(question, paper_id=paper_id, top_k=top_k)
        
        if not contexts:
            return Answer(
                content="根据提供的论文内容，无法找到相关信息来回答此问题。",
                citations=[],
                confidence="low",
                is_answerable=False,
                context_used=[]
            )
        
        # 2. 构建上下文文本
        context_texts = []
        for i, ctx in enumerate(contexts):
            context_text = f"[片段{i+1}] {ctx.text}\n"
            context_text += f"(来源: {ctx.paper_title}, 第{ctx.page_number}页, {ctx.section_type})\n"
            context_texts.append(context_text)
        
        combined_context = "\n".join(context_texts)
        
        # 3. 调用LLM生成答案
        response = self.llm_client.answer_with_citation(
            question=question,
            context=combined_context,
            require_citation=require_citation
        )
        
        answer_text = response.get("answer", "")
        
        # 4. 检测幻觉
        raw_contexts = [ctx.text for ctx in contexts]
        hallucination_check = HallucinationDetector.check_answer(answer_text, raw_contexts)
        
        # 5. 提取引用
        citations = self._extract_citations(answer_text, contexts)
        
        # 6. 判断是否可回答
        is_answerable = "无法找到" not in answer_text and "无法回答" not in answer_text
        
        # 7. 确定置信度
        if not is_answerable:
            confidence = "low"
        elif hallucination_check["has_issues"]:
            confidence = hallucination_check["confidence"]
        else:
            confidence = "high"
        
        return Answer(
            content=answer_text,
            citations=citations,
            confidence=confidence,
            is_answerable=is_answerable,
            context_used=raw_contexts
        )
    
    def ask_with_verification(
        self,
        question: str,
        paper_id: Optional[str] = None,
        verification_rounds: int = 1
    ) -> Answer:
        """
        带验证的问答（多轮验证减少幻觉）
        
        Args:
            question: 问题
            paper_id: 指定论文ID
            verification_rounds: 验证轮数
            
        Returns:
            Answer对象
        """
        # 第一轮：获取初始答案
        answer = self.ask(question, paper_id=paper_id)
        
        if not answer.is_answerable:
            return answer
        
        # 验证轮
        for round_num in range(verification_rounds):
            # 构建验证提示
            verification_prompt = f"""请验证以下答案是否完全基于提供的上下文，没有添加外部知识：

问题：{question}

答案：{answer.content}

使用的上下文：
"""
            for i, ctx in enumerate(answer.context_used[:3]):
                verification_prompt += f"\n上下文{i+1}:\n{ctx[:500]}...\n"
            
            verification_prompt += """
请分析：
1. 答案中的每个事实是否都能在上下文中找到依据？
2. 是否有任何外部知识或推测？
3. 如果有问题，请指出具体问题。

请以JSON格式输出：
{
    "is_valid": true/false,
    "issues": ["问题1", "问题2"],
    "corrected_answer": "修正后的答案（如果需要）"
}"""
            
            # 调用LLM进行验证
            from .llm_client import Message
            messages = [
                Message(role="system", content="你是一个严格的答案验证专家。请仔细检查答案的事实准确性。"),
                Message(role="user", content=verification_prompt)
            ]
            
            try:
                verification_response = self.llm_client.chat(messages, temperature=0.1)
                import json
                
                # 尝试解析验证结果
                content = verification_response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                verification_result = json.loads(content.strip())
                
                # 如果验证不通过，使用修正后的答案
                if not verification_result.get("is_valid", True):
                    if verification_result.get("corrected_answer"):
                        answer.content = verification_result["corrected_answer"]
                    answer.confidence = "medium"
                    
            except Exception as e:
                # 验证失败不影响原答案
                pass
        
        return answer
    
    def _extract_citations(
        self,
        answer: str,
        contexts: List[RetrievedContext]
    ) -> List[Dict[str, Any]]:
        """
        从答案中提取引用
        
        Args:
            answer: 答案文本
            contexts: 检索到的上下文
            
        Returns:
            引用列表
        """
        citations = []
        
        # 查找引用标记 [Page X] 或 [Section: Name]
        page_pattern = r'\[Page\s+(\d+)\]'
        section_pattern = r'\[Section:\s*([^\]]+)\]'
        
        page_matches = re.findall(page_pattern, answer)
        section_matches = re.findall(section_pattern, answer)
        
        # 匹配到对应的上下文
        for page_num in page_matches:
            for ctx in contexts:
                if str(ctx.page_number) == page_num:
                    citations.append({
                        "type": "page",
                        "page": ctx.page_number,
                        "paper": ctx.paper_title,
                        "text": ctx.text[:200] + "..." if len(ctx.text) > 200 else ctx.text
                    })
                    break
        
        for section_name in section_matches:
            for ctx in contexts:
                if section_name.lower() in ctx.section_type.lower():
                    citations.append({
                        "type": "section",
                        "section": section_name,
                        "paper": ctx.paper_title,
                        "text": ctx.text[:200] + "..." if len(ctx.text) > 200 else ctx.text
                    })
                    break
        
        return citations
    
    def compare_papers(
        self,
        question: str,
        paper_ids: List[str]
    ) -> Dict[str, Any]:
        """
        对比多篇论文回答同一问题
        
        Args:
            question: 问题
            paper_ids: 论文ID列表
            
        Returns:
            对比结果
        """
        results = {}
        
        for paper_id in paper_ids:
            answer = self.ask(question, paper_id=paper_id)
            results[paper_id] = {
                "answer": answer.content,
                "confidence": answer.confidence,
                "is_answerable": answer.is_answerable,
                "citations": answer.citations
            }
        
        # 生成对比总结
        comparison_summary = self._generate_comparison(results, question)
        
        return {
            "individual_answers": results,
            "comparison": comparison_summary
        }
    
    def _generate_comparison(
        self,
        results: Dict[str, Any],
        question: str
    ) -> str:
        """生成对比总结"""
        answerable_results = {
            k: v for k, v in results.items() if v["is_answerable"]
        }
        
        if not answerable_results:
            return "没有论文包含回答此问题的相关信息。"
        
        summary = f"针对问题'{question}'，共找到{len(answerable_results)}篇论文的相关信息。\n\n"
        
        for paper_id, result in answerable_results.items():
            summary += f"论文 {paper_id}:\n"
            summary += f"- 置信度: {result['confidence']}\n"
            summary += f"- 答案摘要: {result['answer'][:200]}...\n\n"
        
        return summary


class MultiHopQA:
    """多跳问答 - 处理需要多步推理的复杂问题"""
    
    def __init__(self, qa_system: QASystem):
        self.qa_system = qa_system
    
    def decompose_question(self, complex_question: str) -> List[str]:
        """
        将复杂问题分解为子问题
        
        Args:
            complex_question: 复杂问题
            
        Returns:
            子问题列表
        """
        from .llm_client import Message
        
        system_prompt = """你是一个问题分解专家。请将复杂问题分解为2-4个简单的子问题，每个子问题都应该能独立回答。
输出格式：每行一个子问题，不要编号。"""
        
        user_prompt = f"请将以下问题分解为子问题：\n\n{complex_question}"
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = self.qa_system.llm_client.chat(messages, temperature=0.3)
        
        sub_questions = [
            q.strip() for q in response.content.split('\n')
            if q.strip() and not q.strip().startswith('```')
        ]
        
        return sub_questions[:4]  # 最多4个子问题
    
    def answer(
        self,
        question: str,
        paper_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        回答复杂问题
        
        Args:
            question: 复杂问题
            paper_id: 指定论文ID
            
        Returns:
            包含子问题答案和综合答案的字典
        """
        # 1. 分解问题
        sub_questions = self.decompose_question(question)
        
        # 2. 回答每个子问题
        sub_answers = []
        for sub_q in sub_questions:
            answer = self.qa_system.ask(sub_q, paper_id=paper_id)
            sub_answers.append({
                "question": sub_q,
                "answer": answer.content,
                "confidence": answer.confidence,
                "citations": answer.citations
            })
        
        # 3. 综合答案
        combined_answer = self._synthesize_answer(question, sub_answers)
        
        return {
            "original_question": question,
            "sub_questions": sub_answers,
            "final_answer": combined_answer,
            "reasoning_chain": self._build_reasoning_chain(sub_answers)
        }
    
    def _synthesize_answer(
        self,
        original_question: str,
        sub_answers: List[Dict[str, Any]]
    ) -> str:
        """综合子问题答案"""
        from .llm_client import Message
        
        context = f"原始问题: {original_question}\n\n子问题及答案:\n"
        for i, sa in enumerate(sub_answers, 1):
            context += f"\n{i}. {sa['question']}\n   答案: {sa['answer']}\n"
        
        system_prompt = """你是一个答案综合专家。请基于子问题的答案，生成一个完整、连贯的最终答案。
要求：
1. 只使用子问题答案中的信息
2. 保持逻辑清晰
3. 不要添加新的信息"""
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=context)
        ]
        
        response = self.qa_system.llm_client.chat(messages, temperature=0.3)
        return response.content
    
    def _build_reasoning_chain(self, sub_answers: List[Dict[str, Any]]) -> str:
        """构建推理链"""
        chain = "推理过程:\n"
        for i, sa in enumerate(sub_answers, 1):
            chain += f"{i}. {sa['question']} -> {sa['confidence']}置信度回答\n"
        return chain
