# 定时关机小程序

一个单文件的 Python 程序（只用标准库），支持 Windows / macOS / Linux。

## 功能
- **倒计时**：N 小时 M 分钟后关机，带 15 分钟 / 30 分钟 / 1 小时 / 2 小时快捷按钮
- **指定时间**：到某个时刻（如 `23:30`）关机，该时刻已过则顺延到明天
- **操作类型**：关机 / 重启 / 休眠
- 实时显示剩余时间，到点前 60 秒弹窗置顶提醒，随时可以取消

## 使用
需要 Python 3（Windows 安装时勾选 tcl/tk，默认就有）。

图形界面：
```bash
python shutdown_timer.py
```
Windows 下也可以直接双击 `定时关机.bat`。

### 桌面快捷方式
- Windows：双击 `创建桌面快捷方式.bat`，桌面上会出现「定时关机」图标，之后双击图标即可打开（不会弹黑色命令行窗口）
- 任何系统：运行 `python shutdown_timer.py --shortcut`
  （macOS 生成 `定时关机.command`，Linux 生成 `定时关机.desktop`）

快捷方式指向当前文件夹里的程序，创建后请不要移动或删除这个文件夹。

命令行：
```bash
python shutdown_timer.py --in 90                    # 90 分钟后关机
python shutdown_timer.py --at 23:30                 # 23:30 关机
python shutdown_timer.py --at 7:00 --action restart # 7:00 重启
python shutdown_timer.py --in 1 --dry-run           # 演示模式，不会真关机
```
命令行模式按 `Ctrl+C` 取消。

## 注意
- 程序需要保持运行，关闭窗口即取消定时。
- Linux 下关机可能需要 `sudo`。
