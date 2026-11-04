# baojian-gui Skill

办公计算机终端保密检查系统（baojian-gui）的开发、打包与 **Windows 7 兼容分发**知识库，沉淀为一个可复用的 WorkBuddy skill。

本 skill 不收集任何涉密扫描规则，只固化**工程经验**：如何让一个 PyQt5 / Python GUI 程序打包成能在 Win7 上运行的原生 EXE，以及相关的代码模式。可安全公开、可跨项目复用。

## 适用场景

- 给 **Windows 7 SP1** 打包 PyQt5 / PyInstaller 原生 EXE（最易踩坑的环节）。
- 遇到以下典型故障时的排查依据：
  - 启动报 `api-ms-win-core-path-l1-1-0.dll 找不到`
  - 双击 EXE 一闪而过
  - `DLL load failed while importing _rust` / cryptography 加载失败
  - 图片 OCR 在 Win7 上不工作
- 需要生成中文 PDF 报表（reportlab 字体回退）、编写 OCR 懒加载+降级逻辑、文件级并行扫描。

## 仓库结构

```
baojian-gui/
├── SKILL.md                      # skill 入口：工作流、关键坑位速查、资源索引
├── references/
│   ├── win7-packaging.md         # Win7 打包全景：三轮错误根因纠正、cryptography 修复、
│   │                             #   依赖版本锁、腾讯镜像、CArchiveReader 验证
│   └── source-patterns.md        # 可复用代码模式：OCR 懒加载降级 / 中文 PDF 字体回退 / 并行扫描
├── assets/
│   ├── build_qt.spec             # Win7 专用构建（Python 3.8）
│   └── build_qt_win8.spec        # Win8+ 专用构建（Python 3.13）
└── scripts/
    └── make_bat.py               # 生成 GBK 编码的 Win7 运行库安装 bat
```

## 核心结论速记

| 目标系统 | Python | 运行库要求 | 图片 OCR | 备注 |
|---|---|---|---|---|
| **Win7 SP1** | **3.8** | 需装 VC++ 2015-2022 运行库 + KB2999226 + KB3118401 | 自动降级（仅文件名） | 唯一能原生启动的版本 |
| Win8 / 8.1 / 10 / 11 | 3.13 | 无需任何补丁 | 完整可用 | 速度最快 |

- `api-ms-win-core-path` 启动崩溃的真凶是 **`python39.dll` 本身**（CPython 3.9 起依赖该 DLL，Win7 无）；**根治：改用 Python 3.8 打包**。
- `cryptography` 锁 **41.0.7**（<42），并用 System32 的 2025 版 `vcruntime140.dll/_1.dll` 覆盖 embeddable 自带旧版。
- onnxruntime 全版本仍拽 Win8+ 的 `api-ms-win-core-path` API → Win7 上 OCR 自动降级（仅按文件名），docx/xlsx/pptx/pdf 内容检查不受影响。

完整根因与修复步骤见 `references/win7-packaging.md`。

## 如何使用这个 skill

1. 把本仓库克隆 / 拷贝到 WorkBuddy 的 skills 目录：
   - 用户级：`~/.workbuddy/skills/baojian-gui/`
   - 项目级：`<项目>/.workbuddy/skills/baojian-gui/`
2. 在 WorkBuddy 对话中提到相关任务（如“给 Win7 打包这个 PyQt5 程序”），skill 会自动加载。
3. 需要双版本 EXE 时，直接以 `assets/` 下的两个 spec 为模板跑 `pyinstaller`。
4. 需要 Win7 运行库安装 bat 时，运行 `python scripts/make_bat.py` 生成（GBK 编码，适配 Win7 cmd）。

## 许可

内部工具知识沉淀，按需要自由复用。
