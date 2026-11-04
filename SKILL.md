---
name: baojian-gui
description: "办公计算机终端保密检查系统（baojian-gui）的开发、打包与 Windows 7 兼容分发知识库。当任务涉及 PyQt5 加 PyInstaller 打包原生 EXE、Python 3.8/3.9/3.13 在 Win7/Win8+ 的兼容问题、api-ms-win-core-path 启动崩溃、cryptography/_rust 加载失败、onnxruntime RapidOCR 图片 OCR 在 Win7 自动降级、中文 PDF 报表（reportlab 字体回退）、或任何给 Win7 打包 Python GUI 程序的需求时，使用本 skill。内含双版本构建 spec（Win7=py3.8，Win8+=py3.13）、运行库 bat 生成脚本、依赖版本锁与三轮错误根因纠正记录。"
---

# 办公计算机终端保密检查系统（baojian-gui）开发 Skill

## Overview

本 skill 沉淀「办公计算机终端保密检查系统」小工具从源码到分发的完整开发经验，重点是其 **Windows 7 兼容打包**这一最易踩坑的环节。工具为 PyQt5（Qt5）原生窗口 EXE，采用**双版本同源分发**：同一套源码（main.py / scanner.py / report.py）分别用 Python 3.8（面向 Win7 SP1）与 Python 3.13（面向 Win8/8.1/10/11）打包，功能一致，均支持文件级并行扫描、涉密关键词/密级标识命中、PDF 报表导出、图片 OCR（RapidOCR）。

核心交付物：两份 PyInstaller spec、一份运行库安装 bat 生成脚本、依赖版本锁、以及一份“三轮错误诊断”记录——后者是避免重复踩坑的关键。

## 何时使用

- 需要修改、重新打包或排查 baojian-gui 本体。
- 任何“把 PyQt5/Python GUI 程序打包成能在 Win7 运行的 EXE”的需求（本 skill 的经验可通用）。
- 遇到 `api-ms-win-core-path-l1-1-0.dll 找不到`、双击 EXE 一闪而过、`DLL load failed while importing _rust` 等 Win7 典型故障。
- 需要生成/调整 Win7 运行库安装 bat 或中文 PDF 报表逻辑。

## 项目结构（源码基线）

```
baojian-gui/
├── main.py            # PyQt5 GUI 主窗口 + 扫描调度（~990 行）
├── scanner.py         # 纯逻辑：文件扫描、内容提取、OCR 懒加载+降级、并行（~530 行，无界面可单测）
├── report.py          # reportlab 生成中文 PDF 报表（字体回退 simhei→msyh→simsun→STSong-Light）
├── build_qt.spec      # ★ Win7 专用：Python 3.8 构建
├── build_qt_win8.spec # ★ Win8+ 专用：Python 3.13 构建
└── dist/              # 成品 EXE + 运行库 + bat + 手册
```

> scanner.py 是纯逻辑模块，**沙箱无图形桌面时可在 `QT_QPA_PLATFORM=offscreen` 下单独验证逻辑**，无需 GUI。

## 工作流程

### 1. 双版本打包（核心）

对同一份源码跑两个 spec，产出两个 EXE：

- **Win7 版**（`build_qt.spec`，Python 3.8）：必须先读懂 `references/win7-packaging.md`——**Win7 兼容的所有坑都在这里**。
- **Win8+ 版**（`build_qt_win8.spec`，Python 3.13）：速度更快、OCR 完整，无需任何补丁。

两个 spec 都已剔除未使用的 Qt 模块与 `opencv_videoio_ffmpeg*_64.dll`（约省 30MB），并 `collect_all` 了 onnxruntime/rapidocr。直接复制 `assets/` 下的 spec 作为起点即可。

打包命令（在对应 venv 内）：

```bash
# Win7 版（需在 C:\py38 环境 + 已替换新 vcruntime）
pyinstaller build_qt.spec --onefile --windowed
# Win8+ 版（envs/default py3.13）
pyinstaller build_qt_win8.spec --onefile --windowed
```

> **PyInstaller safe-delete 坑**：重打包时 WorkBuddy 的 safe-delete shim 会拦截它对旧 `dist/*.exe` 的删除（报 trash 失败、EXIT=1）。解决：先把旧 exe `mv` 改名挪开，再打包，不要直接删。

### 2. 生成运行库安装 bat

Win7 目标机首次运行前需装运行库。用 `scripts/make_bat.py` 生成 GBK 编码（无 BOM）的 `安装UCRT补丁_x64.bat`，内容：自动提权 → 装 `vc_redist.x64.exe /install /quiet /norestart` → `wusa KB2999226 /quiet /norestart` → `wusa KB3118401 /quiet /norestart` → 提示重启。bat 必须 GBK 编码，否则 Win7 cmd 中文乱码。

### 3. 验证（沙箱离屏，无 GUI）

GUI 无法在此可视化，只能用离屏启动做存活检测：

```bash
QT_QPA_PLATFORM=offscreen python main.py & PID=$!
sleep 10
kill -0 $PID && echo ALIVE   # ALIVE = 启动无崩溃
```

对打好的 EXE，用 `CArchiveReader`（PyInstaller 内部 API）扫描包内成员，搜 `api-ms-win-core-path` 字符串，确认依赖来源（见 `references/win7-packaging.md` 的验证段）。

### 4. 中文 PDF 报表

reportlab 默认不含中文字体，必须注册字体回退链。直接复用 `report.py` 的 `setup_cn_font()`（simhei → msyh → simsun → STSong-Light CID）。**不要**直接用 reportlab 默认字体写中文，否则导出空白/方块。

## ⚠️ 关键坑位速查（务必先读 references/win7-packaging.md）

1. **启动报 `api-ms-win-core-path-l1-1-0.dll 找不到`** → 真凶是 **`python39.dll` 本身**（CPython 3.9 起用 PathCch 函数依赖该 DLL，Win7 无）。**根治：改用 Python 3.8 打包**（Win7 最后原生支持版本，`python38.dll` 不导入该 DLL）。UCRT 补丁 KB2999226/KB3118401 **不含** 此 DLL，装它们救不了。
2. **`DLL load failed while importing _rust` / cryptography 加载失败** → 把 **`cryptography` 锁 `41.0.7`（<42）**，并把 System32 里 **2025 版 VS2022 的 `vcruntime140.dll` + `vcruntime140_1.dll`** 拷进 `C:\py38\` 覆盖 embeddable 自带的 2021 旧版。
3. **Win7 上图片 OCR 自动降级**（仅按文件名命中）是**预期行为**：onnxruntime 全版本仍用 Win8+ 的 `api-ms-win-core-path` API，Win7 无法加载 → scanner.py 容错降级，docx/xlsx/pptx/pdf 内容提取不受影响。要 OCR 文字识别用 Win8+ 版。
4. **依赖版本锁**不可随意升级（py3.8 与 py3.13 各自独立），详见 `references/win7-packaging.md`。重点：`onnxruntime` py3.13 必须 `1.20.1`（**不能 1.28.0**，与 PyQt5 旧 vcruntime140 冲突导致“DLL 初始化例程失败”）；`reportlab` 在 py3.9/3.8 必须 `4.2.5`（5.x 有 3.10+ 守卫）。

## 资源索引

- **references/win7-packaging.md** — Win7 打包全景：三轮错误根因纠正、VC++ 运行库、cryptography 修复、依赖锁、腾讯镜像、验证方法。
- **references/source-patterns.md** — scanner.py（OCR 懒加载/降级/线程锁/超时/并行扫描）、report.py（中文 PDF 字体回退）的可复用代码模式。
- **assets/build_qt.spec** — Win7（py3.8）构建 spec 模板。
- **assets/build_qt_win8.spec** — Win8+（py3.13）构建 spec 模板。
- **scripts/make_bat.py** — 生成 GBK 编码的 Win7 运行库安装 bat。
