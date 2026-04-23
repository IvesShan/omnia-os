#!/usr/bin/env python3
"""
Omnia GUI Manager - Zenity-based Graphical Interface
快速管理 Omnia 系统的图形化工具
"""

import os
import sys
import json
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path

# 配置
OMNIA_DIR = Path.home() / ".omnia"
DB_PATH = OMNIA_DIR / "memory_palace.db"
LOG_PATH = OMNIA_DIR / "logs" / "daemon.log"
CONFIG_PATH = OMNIA_DIR / "config" / "omnia.yaml"
PID_FILE = OMNIA_DIR / "daemon.pid"
BACKUP_DIR = OMNIA_DIR / "backups"

class OmniaGUI:
    def __init__(self):
        self.ensure_dirs()
    
    def ensure_dirs(self):
        """确保必要的目录存在"""
        OMNIA_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    def zenity(self, *args):
        """调用 zenity 命令"""
        try:
            result = subprocess.run(
                ["zenity"] + list(args),
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout.strip()
        except Exception as e:
            return 1, str(e)
    
    def notify(self, title, message, icon="info"):
        """发送桌面通知"""
        subprocess.run([
            "notify-send",
            "-i", icon,
            title,
            message
        ])
    
    def get_daemon_status(self):
        """获取守护进程状态"""
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, 0)  # 检查进程是否存在
                return True, pid
            except (ProcessLookupError, ValueError):
                return False, None
        return False, None
    
    def get_api_status(self):
        """检查 API 服务状态"""
        try:
            import requests
            response = requests.get("http://localhost:8080/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_memory_stats(self):
        """获取记忆统计"""
        if not DB_PATH.exists():
            return {}
        
        stats = {}
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # 统计各类型记忆
            for table in ['facts', 'relations', 'habits', 'timeline']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            stats['total'] = sum(stats.values())
            conn.close()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        
        return stats
    
    def get_db_size(self):
        """获取数据库大小"""
        if DB_PATH.exists():
            size = DB_PATH.stat().st_size
            return f"{size / 1024 / 1024:.2f} MB"
        return "0 MB"
    
    def show_status(self):
        """显示状态仪表盘"""
        # 获取状态
        daemon_running, pid = self.get_daemon_status()
        api_running = self.get_api_status()
        stats = self.get_memory_stats()
        db_size = self.get_db_size()
        
        # 构建状态信息
        status_text = f"""<big><b>Omnia 系统状态</b></big>

<b>守护进程:</b> {'✓ 运行中 (PID: ' + str(pid) + ')' if daemon_running else '✗ 未运行'}
<b>API 服务:</b> {'✓ 就绪' if api_running else '✗ 未响应'}

<b>记忆统计:</b>
  Facts:      {stats.get('facts', 0):>5} 条
  Relations:  {stats.get('relations', 0):>5} 条
  Habits:     {stats.get('habits', 0):>5} 条
  Timeline:   {stats.get('timeline', 0):>5} 条
  ─────────────────────
  总计:       {stats.get('total', 0):>5} 条

<b>数据库大小:</b> {db_size}
<b>数据目录:</b> {OMNIA_DIR}
"""
        
        # 显示对话框
        subprocess.run([
            "zenity",
            "--info",
            "--title=Omnia 状态",
            f"--text={status_text}",
            "--width=500",
            "--height=400"
        ])
    
    def control_daemon(self, action):
        """控制守护进程"""
        if action == "start":
            subprocess.run(["python3", "/home/shan//home/shan/omnia-os/omnia-os/scripts/start_daemon.py"])
            self.notify("Omnia", "守护进程已启动", "system-run")
        
        elif action == "stop":
            daemon_running, pid = self.get_daemon_status()
            if daemon_running and pid:
                try:
                    os.kill(pid, 15)  # SIGTERM
                    PID_FILE.unlink(missing_ok=True)
                    self.notify("Omnia", "守护进程已停止", "system-shutdown")
                except Exception as e:
                    self.zenity("--error", f"--text=停止失败: {e}")
        
        elif action == "restart":
            self.control_daemon("stop")
            import time
            time.sleep(1)
            self.control_daemon("start")
    
    def show_logs(self):
        """显示日志"""
        if not LOG_PATH.exists():
            self.zenity("--error", "--text=日志文件不存在")
            return
        
        # 读取最后 100 行日志
        result = subprocess.run(
            ["tail", "-n", "100", str(LOG_PATH)],
            capture_output=True,
            text=True
        )
        
        # 显示日志
        subprocess.run([
            "zenity",
            "--text-info",
            "--title=Omnia 日志",
            f"--filename=/dev/stdin",
            "--width=800",
            "--height=600",
            "--font=monospace"
        ], input=result.stdout, text=True)
    
    def backup_memory(self):
        """备份记忆"""
        if not DB_PATH.exists():
            self.zenity("--error", "--text=数据库文件不存在")
            return
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"memory_palace_{timestamp}.db"
        
        # 复制文件
        import shutil
        shutil.copy2(DB_PATH, backup_file)
        
        self.notify("Omnia", f"备份完成: {backup_file.name}", "document-save")
        self.zenity("--info", f"--text=备份成功！\n\n文件: {backup_file}\n大小: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    def restore_backup(self):
        """恢复备份"""
        # 列出备份文件
        backups = sorted(BACKUP_DIR.glob("memory_palace_*.db"), reverse=True)
        
        if not backups:
            self.zenity("--error", "--text=没有找到备份文件")
            return
        
        # 选择备份文件
        backup_list = "\n".join([f"{b.name} ({b.stat().st_size / 1024 / 1024:.2f} MB)" for b in backups[:20]])
        
        code, selected = self.zenity(
            "--list",
            "--title=选择备份",
            "--text=选择要恢复的备份文件:",
            "--column=备份文件",
            *[f"{b.name} ({b.stat().st_size / 1024 / 1024:.2f} MB)" for b in backups[:20]]
        )
        
        if code == 0 and selected:
            # 确认恢复
            code2, _ = self.zenity(
                "--question",
                f"--text=确定要恢复备份吗？\n\n这将覆盖当前的记忆数据库！"
            )
            
            if code2 == 0:
                # 找到选中的备份文件
                backup_name = selected.split(" (")[0]
                backup_file = BACKUP_DIR / backup_name
                
                # 恢复
                import shutil
                shutil.copy2(backup_file, DB_PATH)
                
                self.notify("Omnia", "记忆已恢复", "document-revert")
                self.zenity("--info", "--text=恢复成功！")
    
    def search_memory(self):
        """搜索记忆"""
        # 输入搜索词
        code, query = self.zenity(
            "--entry",
            "--title=搜索记忆",
            "--text=输入搜索关键词:",
            "--entry-text="
        )
        
        if code != 0 or not query:
            return
        
        # 搜索数据库
        results = []
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            for table in ['facts', 'relations', 'habits', 'timeline']:
                cursor.execute(f"SELECT * FROM {table} WHERE content LIKE ?", (f"%{query}%",))
                for row in cursor.fetchall():
                    results.append(f"[{table}] {row}")
            
            conn.close()
        except Exception as e:
            self.zenity("--error", f"--text=搜索失败: {e}")
            return
        
        # 显示结果
        if results:
            result_text = "\n\n".join(results[:50])  # 限制显示数量
            subprocess.run([
                "zenity",
                "--text-info",
                "--title=搜索结果",
                f"--text=找到 {len(results)} 条结果\n\n{result_text}",
                "--width=800",
                "--height=600"
            ])
        else:
            self.zenity("--info", "--text=没有找到匹配的记忆")
    
    def show_stats(self):
        """显示详细统计"""
        stats = self.get_memory_stats()
        
        # 获取分类统计
        categories = {}
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT category, COUNT(*) FROM facts GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10")
            for row in cursor.fetchall():
                categories[row[0]] = row[1]
            conn.close()
        except:
            pass
        
        # 构建统计信息
        stats_text = f"""<big><b>Omnia 详细统计</b></big>

<b>记忆分布:</b>
  Facts:      {stats.get('facts', 0):>5} 条
  Relations:  {stats.get('relations', 0):>5} 条
  Habits:     {stats.get('habits', 0):>5} 条
  Timeline:   {stats.get('timeline', 0):>5} 条
  ─────────────────────
  总计:       {stats.get('total', 0):>5} 条

<b>Top 10 分类:</b>
"""
        for cat, count in categories.items():
            stats_text += f"  {cat:<20} {count:>5} 条\n"
        
        # 显示
        subprocess.run([
            "zenity",
            "--info",
            "--title=Omnia 统计",
            f"--text={stats_text}",
            "--width=600",
            "--height=500"
        ])
    
    def edit_config(self):
        """编辑配置文件"""
        if CONFIG_PATH.exists():
            # 使用文本编辑器打开
            subprocess.run(["gedit", str(CONFIG_PATH)])
        else:
            self.zenity("--error", "--text=配置文件不存在")
    
    def show_main_menu(self):
        """显示主菜单"""
        while True:
            # 获取当前状态
            daemon_running, pid = self.get_daemon_status()
            daemon_status = f"守护进程: {'运行中' if daemon_running else '已停止'}"
            
            # 显示主菜单
            code, choice = self.zenity(
                "--list",
                "--title=Omnia 管理器",
                f"--text={daemon_status}",
                "--column=功能",
                "--column=说明",
                "状态", "查看系统状态",
                "启动", "启动守护进程",
                "停止", "停止守护进程",
                "重启", "重启守护进程",
                "日志", "查看系统日志",
                "备份", "备份记忆数据库",
                "恢复", "恢复备份",
                "搜索", "搜索记忆",
                "统计", "详细统计信息",
                "配置", "编辑配置文件",
                "--width=500",
                "--height=450"
            )
            
            if code != 0:  # 用户取消或关闭
                break
            
            # 执行对应功能
            actions = {
                "状态": self.show_status,
                "启动": lambda: self.control_daemon("start"),
                "停止": lambda: self.control_daemon("stop"),
                "重启": lambda: self.control_daemon("restart"),
                "日志": self.show_logs,
                "备份": self.backup_memory,
                "恢复": self.restore_backup,
                "搜索": self.search_memory,
                "统计": self.show_stats,
                "配置": self.edit_config
            }
            
            if choice in actions:
                actions[choice]()


def main():
    # 检查 zenity 是否安装
    result = subprocess.run(["which", "zenity"], capture_output=True)
    if result.returncode != 0:
        print("错误: zenity 未安装")
        print("请运行: sudo apt install zenity")
        sys.exit(1)
    
    # 启动 GUI
    gui = OmniaGUI()
    
    # 如果有命令行参数，直接执行对应功能
    if len(sys.argv) > 1:
        action = sys.argv[1]
        actions = {
            "status": gui.show_status,
            "start": lambda: gui.control_daemon("start"),
            "stop": lambda: gui.control_daemon("stop"),
            "restart": lambda: gui.control_daemon("restart"),
            "logs": gui.show_logs,
            "backup": gui.backup_memory,
            "restore": gui.restore_backup,
            "search": gui.search_memory,
            "stats": gui.show_stats,
            "config": gui.edit_config
        }
        
        if action in actions:
            actions[action]()
        else:
            print(f"未知命令: {action}")
            print("可用命令:", ", ".join(actions.keys()))
            sys.exit(1)
    else:
        # 显示主菜单
        gui.show_main_menu()


if __name__ == "__main__":
    main()
