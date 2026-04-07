"""
Noctua 猫头鹰论文助手 - 真实处理功能

功能：
- 处理论文（生成笔记和数据库）
- 问答（基于论文内容）
- 列出论文和笔记
- 查看统计信息

使用：
    python demo.py
"""

import time
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from paper_agent.noctua_personality import create_noctua
from paper_agent import create_agent


# 全局变量存储 agent 实例
_agent = None


def get_agent():
    """获取或创建 PaperAgent 实例"""
    global _agent
    if _agent is None:
        noctua = create_noctua(enabled=True)
        noctua.print_reaction()
        print("[Noctua] 正在初始化...")
        
        try:
            _agent = create_agent(noctua_enabled=True)
            print("[Noctua] 初始化完成！")
        except Exception as e:
            noctua.print_error("general", str(e))
            raise
    return _agent


def process_paper():
    """处理论文"""
    print("\n" + "=" * 60)
    print("处理论文")
    print("=" * 60)
    
    file_path = input("请输入 PDF 文件路径（默认: ./papers）: ").strip()
    
    # 默认路径
    if not file_path:
        file_path = "./papers"
        print(f"[Noctua] 使用默认路径: {file_path}")
    
    # 如果是目录，列出PDF文件供选择
    path_obj = Path(file_path)
    if path_obj.is_dir():
        pdf_files = list(path_obj.glob("*.pdf"))
        if not pdf_files:
            print(f"[Noctua] 咕？目录中没有找到 PDF 文件: {file_path}")
            return
        
        print(f"\n[Noctua] 找到 {len(pdf_files)} 个 PDF 文件：")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"  {i}. {pdf.name}")
        
        choice = input("\n请选择文件编号（或输入完整路径）: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(pdf_files):
            file_path = str(pdf_files[int(choice) - 1])
        elif choice:
            file_path = choice
        else:
            print("[Noctua] 咕？未选择文件...")
            return
    
    if not Path(file_path).exists():
        print(f"[Noctua] 咕？文件不存在: {file_path}")
        return
    
    tags_input = input("请输入标签（用空格分隔，可选）: ").strip()
    tags = tags_input.split() if tags_input else None
    
    try:
        agent = get_agent()
        
        print("\n[Noctua] 开始处理论文...")
        result = agent.process_paper(
            file_path=file_path,
            create_note=True,
            add_to_db=True,
            tags=tags
        )
        
        if result["success"]:
            print("\n" + "=" * 60)
            print("处理结果：")
            print("=" * 60)
            print(f"论文: {result['paper']['file_name']}")
            print(f"页数: {result['paper']['total_pages']}")
            
            if result.get("note"):
                note_id = result['note']['id']
                # 从agent获取文件名信息
                note_info = None
                for note in agent.note_manager.notes_index["notes"]:
                    if note["id"] == note_id:
                        note_info = note
                        break
                if note_info:
                    print(f"\n笔记已创建!")
                    print(f"  📄 JSON: notes/{note_info['json_file']}")
                    print(f"  📝 Markdown: notes/{note_info['md_file']}")
                else:
                    print(f"\n笔记已创建: {note_id}")
            
            if result.get("db_added"):
                print(f"\n已添加到向量数据库")
            
            print("\n[Noctua] 咕咕~ 论文处理完成！")
        else:
            print(f"\n[Noctua] 处理失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        noctua = create_noctua(enabled=True)
        noctua.print_error("general", str(e))


def ask_question():
    """问答"""
    print("\n" + "=" * 60)
    print("问答")
    print("=" * 60)
    
    question = input("请输入问题: ").strip()
    
    if not question:
        print("[Noctua] 咕？问题不能为空...")
        return
    
    paper_id = input("指定论文 ID（可选，直接回车搜索所有）: ").strip() or None
    
    try:
        agent = get_agent()
        
        print("\n[Noctua] 正在思考问题...")
        answer = agent.ask(
            question=question,
            paper_id=paper_id,
            top_k=5
        )
        
        if answer.get('is_answerable', True):
            print("\n" + "=" * 60)
            noctua = create_noctua(enabled=True)
            noctua.print_answer(answer['answer'])
            print(f"置信度: {answer['confidence']}")
            
            if answer.get('citations'):
                print(f"\n引用:")
                for citation in answer['citations']:
                    print(f"  - {citation.get('paper', 'Unknown')}, Page {citation.get('page', 'N/A')}")
        else:
            noctua = create_noctua(enabled=True)
            noctua.print_error("empty")
            
    except Exception as e:
        noctua = create_noctua(enabled=True)
        noctua.print_error("general", str(e))


def list_papers():
    """列出论文"""
    print("\n" + "=" * 60)
    print("列出论文")
    print("=" * 60)
    
    try:
        agent = get_agent()
        papers = agent.list_papers()
        
        if papers:
            print(f"\n[Noctua] 找到 {len(papers)} 篇论文：")
            for paper in papers:
                print(f"  [论文] {paper['id']}: {paper['title']}")
        else:
            print("\n[Noctua] 咕~ 还没有处理过论文呢")
            
    except Exception as e:
        noctua = create_noctua(enabled=True)
        noctua.print_error("general", str(e))


def list_notes():
    """列出笔记（显示友好的文件名）"""
    print("\n" + "=" * 60)
    print("已读论文列表")
    print("=" * 60)

    try:
        agent = get_agent()
        papers = agent.note_manager.list_papers_summary()

        if papers:
            print(f"\n[Noctua] 共找到 {len(papers)} 篇已读论文：\n")
            for i, paper in enumerate(papers, 1):
                print(f"  {i}. {paper['title']}")
                print(f"     📄 笔记文件: {paper['md_file']}")
                print(f"     📅 阅读时间: {paper['created_at'][:10]}")
                if paper.get('tags'):
                    print(f"     🏷️  标签: {', '.join(paper['tags'])}")
                print()

            # 同时生成/更新阅读列表文件
            reading_list = agent.note_manager.get_reading_list()
            reading_list_path = Path(agent.config.notes_dir) / "README.md"
            with open(reading_list_path, 'w', encoding='utf-8') as f:
                f.write(reading_list)
            print(f"[Noctua] 已生成阅读列表: {reading_list_path}")
        else:
            print("\n[Noctua] 咕~ 还没有读过任何论文呢")

    except Exception as e:
        noctua = create_noctua(enabled=True)
        noctua.print_error("general", str(e))


def show_stats():
    """显示统计信息"""
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    
    try:
        agent = get_agent()
        stats = agent.get_stats()
        
        noctua = create_noctua(enabled=True)
        noctua.print_stats(stats)
        
    except Exception as e:
        noctua = create_noctua(enabled=True)
        noctua.print_error("general", str(e))


def show_menu():
    """显示菜单"""
    print("\n" + "=" * 60)
    print("  Noctua 猫头鹰论文助手")
    print("=" * 60)
    print()
    print("功能选项：")
    print("  1. 处理论文 - 处理 PDF 并生成笔记")
    print("  2. 问答 - 基于论文内容回答问题")
    print("  3. 列出论文 - 列出所有已处理的论文")
    print("  4. 列出笔记 - 列出所有生成的笔记")
    print("  5. 统计信息 - 显示统计信息")
    print()
    print("其他：")
    print("  c. 清屏")
    print("  q. 退出")
    print()


def main():
    """主函数"""
    # 启动问候
    noctua = create_noctua(enabled=True)
    noctua.print_greeting()
    
    functions = {
        '1': ("处理论文", process_paper),
        '2': ("问答", ask_question),
        '3': ("列出论文", list_papers),
        '4': ("列出笔记", list_notes),
        '5': ("统计信息", show_stats),
    }
    
    while True:
        show_menu()
        choice = input("请选择 (1-5, c, q): ").strip().lower()
        
        if choice == 'q':
            print("\n" + "=" * 60)
            print("Noctua: 咕咕~ 感谢使用！再见！")
            print("=" * 60)
            break
        
        elif choice == 'c':
            os.system('cls' if os.name == 'nt' else 'clear')
            continue
        
        elif choice in functions:
            functions[choice][1]()
            print("\n" + "-" * 60)
            input("按 Enter 返回菜单...")
        
        else:
            print("\n无效选择，请重新输入")
            time.sleep(1)


if __name__ == "__main__":
    main()
