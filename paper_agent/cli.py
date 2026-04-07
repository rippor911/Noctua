"""
命令行接口 - 提供便捷的命令行操作
集成 🦉 Noctua 猫头鹰个性化
"""

import os
import sys
import argparse
from pathlib import Path

from .paper_agent import create_agent, AgentConfig
from .noctua_personality import create_noctua, NoctuaProgressBar


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="[Noctua] - 智慧猫头鹰论文阅读助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动 Noctua（带个性化）
  python -m paper_agent process paper.pdf
  
  # 问答
  python -m paper_agent ask "论文的主要贡献是什么？"
  
  # 列出所有论文
  python -m paper_agent list
  
  # 导出笔记
  python -m paper_agent export note_xxx --format markdown
  
  # 禁用个性化（严肃模式）
  python -m paper_agent --no-personality process paper.pdf
        """
    )
    
    # 添加 Noctua 个性化选项
    parser.add_argument(
        "--no-personality",
        action="store_true",
        help="禁用猫头鹰个性化（严肃模式）"
    )
    
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API密钥"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help="API基础URL"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="模型名称"
    )
    parser.add_argument(
        "--papers-dir",
        default="./papers",
        help="论文存放目录"
    )
    parser.add_argument(
        "--notes-dir",
        default="./notes",
        help="笔记存放目录"
    )
    parser.add_argument(
        "--database-dir",
        default="./database",
        help="数据库目录"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # process 命令
    process_parser = subparsers.add_parser("process", help="处理论文")
    process_parser.add_argument("file", help="PDF文件路径")
    process_parser.add_argument("--no-note", action="store_true", help="不创建笔记")
    process_parser.add_argument("--no-db", action="store_true", help="不添加到数据库")
    process_parser.add_argument("--tags", nargs="+", help="标签列表")
    
    # ask 命令
    ask_parser = subparsers.add_parser("ask", help="问答")
    ask_parser.add_argument("question", help="问题")
    ask_parser.add_argument("--paper-id", help="指定论文ID")
    ask_parser.add_argument("--top-k", type=int, default=5, help="检索数量")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出论文或笔记")
    list_parser.add_argument("--notes", action="store_true", help="列出笔记")
    list_parser.add_argument("--tags", nargs="+", help="按标签筛选")
    
    # export 命令
    export_parser = subparsers.add_parser("export", help="导出笔记")
    export_parser.add_argument("note_id", help="笔记ID")
    export_parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="导出格式")
    export_parser.add_argument("--output", help="输出文件路径")
    
    # stats 命令
    stats_parser = subparsers.add_parser("stats", help="显示统计信息")
    
    # clean 命令 - 新增"打扫巢穴"
    clean_parser = subparsers.add_parser("clean", help="打扫巢穴 - 清理临时文件")
    clean_parser.add_argument("--all", action="store_true", help="清理所有数据（包括笔记和数据库）")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建 Noctua 个性化实例
    noctua = create_noctua(enabled=not args.no_personality)
    
    # 打印启动问候
    noctua.print_greeting()
    
    # 创建智能体
    config = AgentConfig(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        papers_dir=args.papers_dir,
        notes_dir=args.notes_dir,
        database_dir=args.database_dir
    )
    
    agent = create_agent(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        papers_dir=config.papers_dir,
        notes_dir=config.notes_dir,
        database_dir=config.database_dir
    )
    
    # 将 noctua 附加到 agent
    agent.noctua = noctua
    
    # 执行命令
    if args.command == "process":
        # 检查时间切换
        transition_msg = noctua.check_time_transition()
        if transition_msg:
            print(f"[Noctua] {transition_msg}\n")
        
        # 显示反应
        noctua.print_reaction()
        
        try:
            result = agent.process_paper(
                args.file,
                create_note=not args.no_note,
                add_to_db=not args.no_db,
                tags=args.tags
            )
            
            if result["success"]:
                print(f"\n[Noctua] {noctua.get_completion_message()}")
                if result.get("note"):
                    print(f"   笔记ID: {result['note']['id']}")
                if result.get("db_added"):
                    print(f"   已添加到向量数据库")
            else:
                noctua.print_error("general", result.get('error', '未知错误'))
                sys.exit(1)
        except Exception as e:
            noctua.print_error("general", str(e))
            sys.exit(1)
    
    elif args.command == "ask":
        # 检查时间切换
        transition_msg = noctua.check_time_transition()
        if transition_msg:
            print(f"[Noctua] {transition_msg}\n")
        
        # 显示反应
        noctua.print_reaction()
        
        try:
            answer = agent.ask(
                args.question,
                paper_id=args.paper_id,
                top_k=args.top_k
            )
            
            if answer.get('is_answerable', True):
                noctua.print_answer(answer['answer'])
                print(f"置信度: {answer['confidence']}")
                if answer.get('citations'):
                    print(f"\n引用:")
                    for citation in answer['citations']:
                        print(f"  - {citation.get('paper', 'Unknown')}, Page {citation.get('page', 'N/A')}")
            else:
                noctua.print_error("empty")
                
        except Exception as e:
            noctua.print_error("general", str(e))
            sys.exit(1)
    
    elif args.command == "list":
        try:
            if args.notes:
                notes = agent.list_notes(tags=args.tags)
                if not noctua.enabled:
                    print(f"\n共 {len(notes)} 条笔记:")
                else:
                    print(f"\n[Noctua] 我在巢穴里找到了 {len(notes)} 份笔记:")
                    
                for note in notes:
                    print(f"  [笔记] {note['id']}: {note['paper_title']}")
                    if note.get('tags'):
                        print(f"     标签: {', '.join(note['tags'])}")
            else:
                papers = agent.list_papers()
                if not noctua.enabled:
                    print(f"\n共 {len(papers)} 篇论文:")
                else:
                    print(f"\n[Noctua] 我的巢穴里有 {len(papers)} 篇论文:")
                    
                for paper in papers:
                    print(f"  📄 {paper['id']}: {paper['title']}")
        except Exception as e:
            noctua.print_error("general", str(e))
            sys.exit(1)
    
    elif args.command == "export":
        try:
            content = agent.export_note(args.note_id, args.format)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(content)
                if noctua.enabled:
                    print(f"[Noctua] 已经整理好了！导出到: {args.output}")
                else:
                    print(f"已导出到: {args.output}")
            else:
                print(content)
        except Exception as e:
            noctua.print_error("general", str(e))
            sys.exit(1)
    
    elif args.command == "stats":
        try:
            stats = agent.get_stats()
            noctua.print_stats(stats)
        except Exception as e:
            noctua.print_error("general", str(e))
            sys.exit(1)
    
    elif args.command == "clean":
        # 打扫巢穴功能
        if noctua.enabled:
            print("\n[Noctua] 开始打扫巢穴...")
            print("   (整理羽毛) 咕咕~")
        else:
            print("\n清理临时文件...")
        
        try:
            import shutil
            
            # 清理数据库
            db_path = Path(args.database_dir)
            if db_path.exists():
                shutil.rmtree(db_path)
                if noctua.enabled:
                    print("   [垃圾桶] 清理了数据库缓存")
                
            if args.all:
                # 清理笔记
                notes_path = Path(args.notes_dir)
                if notes_path.exists():
                    shutil.rmtree(notes_path)
                    if noctua.enabled:
                        print("   [垃圾桶] 清理了所有笔记")
                
                # 清理论文
                papers_path = Path(args.papers_dir)
                if papers_path.exists():
                    shutil.rmtree(papers_path)
                    if noctua.enabled:
                        print("   [垃圾桶] 清理了论文目录")
            
            if noctua.enabled:
                print("\n[Noctua] 巢穴打扫完毕！咕咕~ 现在整洁多了！")
            else:
                print("\n清理完成")
                
        except Exception as e:
            noctua.print_error("general", str(e))
            sys.exit(1)


if __name__ == "__main__":
    main()
