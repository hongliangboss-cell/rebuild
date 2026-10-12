#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时关机小程序（Windows / macOS / Linux）

两种定时方式：
  1. 倒计时：N 小时 M 分钟后关机
  2. 指定时间：在某个时刻（如 23:30）关机，若该时刻已过则顺延到明天

可选操作：关机 / 重启 / 休眠（仅 Windows、Linux）
到点前 60 秒会弹出提醒，可随时取消。

用法：
  图形界面：  python shutdown_timer.py
  命令行：    python shutdown_timer.py --in 90        # 90 分钟后关机
              python shutdown_timer.py --at 23:30     # 23:30 关机
              python shutdown_timer.py --at 23:30 --action restart
  桌面快捷方式：python shutdown_timer.py --shortcut
"""

import argparse
import datetime as dt
import os
import platform
import subprocess
import sys
import time

SYSTEM = platform.system()

ACTIONS = {"shutdown": "关机", "restart": "重启", "hibernate": "休眠"}


def build_command(action):
    """返回执行对应电源操作的系统命令。"""
    if SYSTEM == "Windows":
        return {
            "shutdown": ["shutdown", "/s", "/t", "0"],
            "restart": ["shutdown", "/r", "/t", "0"],
            "hibernate": ["shutdown", "/h"],
        }[action]
    if SYSTEM == "Darwin":
        return {
            "shutdown": ["osascript", "-e", 'tell app "System Events" to shut down'],
            "restart": ["osascript", "-e", 'tell app "System Events" to restart'],
            "hibernate": ["pmset", "sleepnow"],
        }[action]
    # Linux
    return {
        "shutdown": ["systemctl", "poweroff"],
        "restart": ["systemctl", "reboot"],
        "hibernate": ["systemctl", "hibernate"],
    }[action]


def execute(action, dry_run=False):
    cmd = build_command(action)
    if dry_run:
        print("[演示模式] 将执行：", " ".join(cmd))
        return
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:  # noqa: BLE001
        print("执行失败：", e, file=sys.stderr)
        if SYSTEM == "Linux":
            print("提示：可能需要 sudo 权限运行。", file=sys.stderr)
        raise


def parse_target(minutes=None, at=None):
    """根据倒计时分钟数或 HH:MM 计算目标时间。"""
    now = dt.datetime.now()
    if minutes is not None:
        if minutes <= 0:
            raise ValueError("分钟数必须大于 0")
        return now + dt.timedelta(minutes=minutes)
    try:
        t = dt.datetime.strptime(at.strip().replace("：", ":"), "%H:%M").time()
    except ValueError:
        raise ValueError("时间格式应为 HH:MM，例如 23:30")
    target = dt.datetime.combine(now.date(), t)
    if target <= now:
        target += dt.timedelta(days=1)
    return target


def fmt_remaining(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------- 桌面快捷方式
SHORTCUT_NAME = "定时关机"


def desktop_dir():
    if SYSTEM == "Windows":
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True, check=True)
        return out.stdout.strip()
    if SYSTEM == "Linux":
        try:
            out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except FileNotFoundError:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def create_shortcut():
    """在桌面创建启动图形界面的快捷方式，返回快捷方式路径。"""
    script = os.path.abspath(__file__)
    desktop = desktop_dir()
    os.makedirs(desktop, exist_ok=True)

    if SYSTEM == "Windows":
        # 用 pythonw 启动，不弹黑色命令行窗口
        exe = sys.executable
        pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(pythonw):
            exe = pythonw
        path = os.path.join(desktop, SHORTCUT_NAME + ".lnk")
        env = dict(os.environ, SC_PATH=path, SC_EXE=exe, SC_SCRIPT=script,
                   SC_DIR=os.path.dirname(script))
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:SC_PATH);"
              "$s.TargetPath=$env:SC_EXE;"
              "$s.Arguments='\"'+$env:SC_SCRIPT+'\"';"
              "$s.WorkingDirectory=$env:SC_DIR;"
              "$s.IconLocation='shell32.dll,27';"
              "$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, check=True)
        return path

    if SYSTEM == "Darwin":
        path = os.path.join(desktop, SHORTCUT_NAME + ".command")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'#!/bin/sh\nnohup "{sys.executable}" "{script}" >/dev/null 2>&1 &\n')
    else:
        path = os.path.join(desktop, SHORTCUT_NAME + ".desktop")
        with open(path, "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\nType=Application\n"
                    f"Name={SHORTCUT_NAME}\n"
                    f'Exec="{sys.executable}" "{script}"\n'
                    "Icon=system-shutdown\nTerminal=false\n")
    os.chmod(path, 0o755)
    return path


# ---------------------------------------------------------------- 命令行模式
def run_cli(args):
    target = parse_target(args.minutes, args.at)
    name = ACTIONS[args.action]
    print(f"将在 {target:%Y-%m-%d %H:%M:%S} {name}。按 Ctrl+C 取消。")
    try:
        while True:
            left = (target - dt.datetime.now()).total_seconds()
            if left <= 0:
                break
            print(f"\r剩余 {fmt_remaining(left)}  ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n已取消。")
        return
    print(f"\n正在{name}...")
    execute(args.action, args.dry_run)


# ---------------------------------------------------------------- 图形界面
def run_gui(dry_run=False):
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("定时关机")
    root.resizable(False, False)

    state = {"target": None, "job": None, "warned": False}

    mode = tk.StringVar(value="countdown")
    hours = tk.StringVar(value="1")
    mins = tk.StringVar(value="0")
    at_time = tk.StringVar(value=(dt.datetime.now() + dt.timedelta(hours=1)).strftime("%H:%M"))
    action = tk.StringVar(value="shutdown")
    status = tk.StringVar(value="未设置定时")
    remaining = tk.StringVar(value="--:--:--")

    frm = ttk.Frame(root, padding=16)
    frm.grid()

    # 定时方式
    ttk.Radiobutton(frm, text="倒计时", variable=mode, value="countdown").grid(row=0, column=0, sticky="w")
    cd = ttk.Frame(frm)
    cd.grid(row=0, column=1, sticky="w", pady=4)
    ttk.Spinbox(cd, from_=0, to=99, width=4, textvariable=hours).pack(side="left")
    ttk.Label(cd, text="小时").pack(side="left", padx=(2, 8))
    ttk.Spinbox(cd, from_=0, to=59, width=4, textvariable=mins).pack(side="left")
    ttk.Label(cd, text="分钟后").pack(side="left", padx=2)

    ttk.Radiobutton(frm, text="指定时间", variable=mode, value="at").grid(row=1, column=0, sticky="w")
    at = ttk.Frame(frm)
    at.grid(row=1, column=1, sticky="w", pady=4)
    ttk.Entry(at, width=8, textvariable=at_time).pack(side="left")
    ttk.Label(at, text="(HH:MM，已过则为明天)").pack(side="left", padx=4)

    # 快捷按钮
    quick = ttk.Frame(frm)
    quick.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)
    ttk.Label(quick, text="快捷：").pack(side="left")
    for m in (15, 30, 60, 120):
        label = f"{m}分钟" if m < 60 else f"{m // 60}小时"
        ttk.Button(quick, text=label, width=7,
                   command=lambda m=m: (mode.set("countdown"), hours.set(str(m // 60)),
                                        mins.set(str(m % 60)), start())).pack(side="left", padx=2)

    # 操作类型
    act = ttk.Frame(frm)
    act.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
    ttk.Label(act, text="操作：").pack(side="left")
    for key, name in ACTIONS.items():
        ttk.Radiobutton(act, text=name, variable=action, value=key).pack(side="left", padx=4)

    # 倒计时显示
    ttk.Label(frm, textvariable=remaining, font=("Consolas", 28, "bold")).grid(row=4, column=0, columnspan=2, pady=(10, 0))
    ttk.Label(frm, textvariable=status, foreground="#555").grid(row=5, column=0, columnspan=2, pady=(0, 10))

    btns = ttk.Frame(frm)
    btns.grid(row=6, column=0, columnspan=2)
    start_btn = ttk.Button(btns, text="开始", width=10)
    cancel_btn = ttk.Button(btns, text="取消", width=10, state="disabled")
    start_btn.pack(side="left", padx=6)
    cancel_btn.pack(side="left", padx=6)

    def tick():
        left = (state["target"] - dt.datetime.now()).total_seconds()
        if left <= 0:
            remaining.set("00:00:00")
            name = ACTIONS[action.get()]
            status.set(f"正在{name}...")
            root.update()
            try:
                execute(action.get(), dry_run)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("失败", f"{name}失败：{e}")
            cancel()
            return
        remaining.set(fmt_remaining(left))
        if left <= 60 and not state["warned"]:
            state["warned"] = True
            root.deiconify()
            root.lift()
            root.attributes("-topmost", True)
            root.after(100, lambda: root.attributes("-topmost", False))
            status.set(f"⚠ 即将{ACTIONS[action.get()]}！如需取消请点「取消」")
        state["job"] = root.after(500, tick)

    def start():
        try:
            if mode.get() == "countdown":
                total = int(hours.get() or 0) * 60 + int(mins.get() or 0)
                target = parse_target(minutes=total)
            else:
                target = parse_target(at=at_time.get())
        except ValueError as e:
            messagebox.showwarning("输入有误", str(e))
            return
        if state["job"]:
            root.after_cancel(state["job"])
        state.update(target=target, warned=False)
        status.set(f"将于 {target:%m-%d %H:%M:%S} {ACTIONS[action.get()]}")
        start_btn.config(text="重新设置")
        cancel_btn.config(state="normal")
        tick()

    def cancel():
        if state["job"]:
            root.after_cancel(state["job"])
        state.update(target=None, job=None, warned=False)
        remaining.set("--:--:--")
        status.set("已取消定时")
        start_btn.config(text="开始")
        cancel_btn.config(state="disabled")

    def on_close():
        if state["target"] and not messagebox.askyesno("退出", "关闭窗口将取消定时，确定退出吗？"):
            return
        root.destroy()

    start_btn.config(command=start)
    cancel_btn.config(command=cancel)
    root.protocol("WM_DELETE_WINDOW", on_close)
    if dry_run:
        root.title("定时关机（演示模式）")
    root.mainloop()


def main():
    p = argparse.ArgumentParser(description="定时关机小程序")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--in", dest="minutes", type=float, help="多少分钟后执行")
    g.add_argument("--at", help="在指定时间执行，格式 HH:MM")
    p.add_argument("--action", choices=ACTIONS.keys(), default="shutdown", help="shutdown/restart/hibernate")
    p.add_argument("--dry-run", action="store_true", help="演示模式：到点只打印命令，不真正关机")
    p.add_argument("--shortcut", action="store_true", help="在桌面创建快捷方式")
    args = p.parse_args()

    if args.shortcut:
        print("已创建桌面快捷方式：", create_shortcut())
        return

    if args.minutes is not None or args.at:
        try:
            run_cli(args)
        except ValueError as e:
            p.error(str(e))
    else:
        run_gui(args.dry_run)


if __name__ == "__main__":
    main()
