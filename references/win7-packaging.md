# Win7 兼容打包全景（baojian-gui）

本文档记录把 PyQt5/Python GUI 打包成可在 **Windows 7 SP1（64 位）** 运行的 EXE 时踩过的所有坑，以及最终正确的解法。经验对同类 Win7 打包需求通用。

---

## 0. 一句话结论

| 目标系统 | Python | 运行库要求 | 图片 OCR | 备注 |
|---|---|---|---|---|
| **Win7 SP1** | **3.8** | 需装 VC++ 2015-2022 运行库 + KB2999226 + KB3118401 | 自动降级（仅文件名） | 唯一能原生启动的版本 |
| Win8 / 8.1 / 10 / 11 | 3.13 | 无需任何补丁 | 完整可用 | 速度最快 |

**不要用 Python 3.9 给 Win7 打包**（见第 1 节）。**Python 3.8 是最后一个原生支持 Win7 的版本**。

---

## 1. 第一轮错误：误判为“缺 UCRT 补丁 KB2999226 / KB3118401”

**现象**：Win7 双击 EXE 报 `api-ms-win-core-path-l1-1-0.dll 找不到`。
**错误判断**：以为装微软 UCRT 补丁就能解决，于是指引用户装 KB2999226 / KB3118401。
**为什么错**：解包这两个 MSU → 其 payload CAB 里的 `amd64_..._apifwd-win7_*` 目录只含 7 个 `api-ms-win-core-*`（file/synch/timezone/processthreads/xstate/localization/file-l2），`amd64_..._ucrt_*` 含 `ucrtbase` + `api-ms-win-crt-*`。**两者都不含 `path`**。KB 永远救不了这个错。

> ✅ 这两个补丁仍有价值（补足 `api-ms-win-crt-*` 等系统级 UCRT），但它们**不是**解决 `api-ms-win-core-path` 的钥匙。

---

## 2. 第二轮错误：误判为“OCR 引擎 onnxruntime 拽 DLL”

**现象**：仍报 `api-ms-win-core-path-l1-1-0.dll 找不到`。
**错误判断**：以为是 rapidocr_onnxruntime / onnxruntime 在拽这个 DLL，于是从 Win7 spec 里把 OCR 整套剔除（exe 从 135MB → 77MB）。
**为什么错**：用 PyInstaller 的 `CArchiveReader` 扫描打好的 EXE 内全部 139 个 DLL/PYD 成员，搜 `api-ms-win-core-path` 导入字符串——**唯一命中的是 `python39.dll` 本身**，onnxruntime 当时不在包内（已排除），根本不是它。剔除 OCR 后 EXE 仍崩溃，证明根因不在 OCR。

> ✅ **CArchiveReader 取证法**（必会）：`ar = CArchiveReader(path_to_exe)`，`ar.toc` 是 `{name: (...,...)}` 字典，`ar.extract(name)` 返回解压后的 bytes；对每个成员搜 `b"api-ms-win-core-path"` 即可定位到底是哪个 DLL 拽了它。

---

## 3. 第三轮（正确）：真凶是 `python39.dll` 本身 → 改用 Python 3.8

**根因**：
- CPython **3.9 起**，`python39.dll` 改用 `PathCch` 系列函数（处理长路径），其导入表包含 `api-ms-win-core-path-l1-1-0.dll`。
- Windows 7 **没有**这套 API 集（Win8+ 才有），所以 3.9 打包的 EXE 在 Win7 启动即崩。
- **Python 3.8 是最后一个原生支持 Win7 的版本**，`python38.dll` 根本不导入 `api-ms-win-core-path`。

**根治动作**：
1. 在 `C:\py38` 部署 **embeddable Python 3.8.10**：编辑 `python38._pth` 启用 site（`import site` 取消注释，并含 `Lib`、`Lib/site-packages`），使 pip 可用。
2. 把 Win7 版 spec 改为 `build_qt.spec`（Python 3.8），**恢复包含** onnxruntime/rapidocr（让 Win8+ 上 OCR 可用，Win7 上自动降级）。
3. 用 `CArchiveReader` 复扫确认：`python38.dll` 不再命中 `api-ms-win-core-path` → 启动崩溃根除。沙箱 `QT_QPA_PLATFORM=offscreen` 启动验证 ALIVE、无崩溃。

---

## 4. 第四个坑（py3.8 首版仍崩）：`DLL load failed while importing _rust`

**现象**：换 3.8 后，Win7 启动报 `DLL load failed while importing _rust: 找不到指定的程序`（来自 cryptography 的 Rust 扩展 `_rust.pyd`，ERROR_PROC_NOT_FOUND）。
**根因**：
- cryptography 47 的 `_rust.pyd` 需要比 Win7 自带（及 embeddable py3.8 自带的 2021 版）`VCRUNTIME140.dll` 更新的符号。
- embeddable py3.8 自带的 `vcruntime140.dll`(2021) + `vcruntime140_1.dll` 偏旧。

**修复两招（缺一不可）**：
1. **pin `cryptography==41.0.7`**（<42；42.0.0 起工具链变新、不再兼容 Win7）。41.0.7 的 `_rust.pyd` 不导入 `api-ms-win-core-path`，只依赖 `VCRUNTIME140` + `api-ms-win-crt-*`。
2. 把 **`C:\Windows\System32\vcruntime140.dll`（2025/VS2022）+ `vcruntime140_1.dll`** 拷进 **`C:\py38\`**，覆盖 embeddable 自带的 2021 旧版，让 PyInstaller 打进 exe 的是新 vcruntime。

**复扫确认**：exe 内 `python38.dll` 不含 path；`_rust.pyd` 也不含；仅 `onnxruntime` 的 dll/pyd 含（→ Win7 上 OCR 降级，已容错）。离屏启动 ALIVE。

> pdfplumber 0.x 仍拉 cryptography，故 py3.8 环境必须 cryptography<42（见第 6 节版本锁）。

---

## 5. onnxruntime 在 Win7 上仍拽 path → OCR 自动降级（设计如此）

`CArchiveReader` 扫描证实：onnxruntime 的 `onnxruntime.dll` / `onnxruntime_pybind11_state.pyd` 仍导入 `api-ms-win-core-path`（已验证 1.16 / 1.17 / 1.18 / 1.19.2 全部版本均如此，无 py3.8 兼容版可绕过）。因此：

- **Win7 上 OCR 引擎无法加载** → scanner.py 容错降级为「仅按文件名命中」，程序不崩溃，docx/xlsx/pptx/pdf 内容提取完全正常。
- **Win8+ 上 OCR 正常**。
- 这是预期行为，不是 bug，不要试图“修”onnxruntime（无解）。如需在 Win7 上做图片 OCR，目前不可行，文档需写明此限制。

---

## 6. 依赖版本锁（务必遵守，否则打包/运行崩）

### 6.1 Win7 构建环境（C:\py38，腾讯镜像安装）

```
PyQt5==5.15.11
reportlab==4.2.5
onnxruntime==1.19.2
opencv-python-headless==5.0.0.93
PyInstaller==6.22.3
rapidocr-onnxruntime==1.4.4
cryptography==41.0.7
python-docx==1.1.2          # 腾讯镜像最高只到 1.1.2，1.2.0 不在镜像
pdfplumber==0.11.4          # 0.11.8 需 pdfminer.six==20251107、0.11.6 需 20250327，镜像均缺；
                            # 0.11.4 可配 pdfminer.six 20231228
openpyxl==3.1.5
python-pptx==1.0.2
```

安装用：
```bash
C:\py38\python.exe -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple/ <包==版本>
```

### 6.2 Win8+ 构建环境（envs/default，Python 3.13）

```
PyQt5==5.15.11
reportlab==5.x              # py3.13 可用 5.x
onnxruntime==1.20.1         # ⚠️ 不能 1.28.0！与 PyQt5 自带(较旧)的 vcruntime140 不兼容，
                            #   frozen exe 内 OCR 一触发就"DLL 初始化例程失败"
opencv-python-headless==5.0.0.93
PyInstaller==6.22.3 (或更新)
rapidocr-onnxruntime==1.4.4
```

### 6.3 通用注意

- `reportlab` 在 **py3.9 / py3.8** 必须 **==4.2.5**（5.x 有 3.10+ 守卫，import 即崩）；py3.13 可用 5.x。
- `onnxruntime`：py3.9 锁 1.19.2；py3.13 锁 1.20.1（不能 1.28.0）。
- opencv 两个 venv 都用 `opencv-python-headless==5.0.0.93`（headless 去掉 Qt5 GUI dll；普通版也行但多 GUI 依赖）。

---

## 7. 镜像与 pip 环境

- **用腾讯镜像**：`--index-url https://mirrors.cloud.tencent.com/pypi/simple/`（实测 20MB/s）。
- **不要用官方 pypi.org**（被限速 ~16KB/s，50MB 包要几十分钟）。
- py39 venv、envs/default(py3.13)、C:\py38 三个环境都能用该镜像。
- pip 安装长耗时包时，避免 `| tail` 掩盖真实退出码；写日志文件 + 后台运行 + 长 timeout（120s+）更稳。

---

## 8. PyInstaller 打包实操坑

- **safe-delete shim 拦截删旧 exe**：重打包时 WorkBuddy 的 safe-delete 会拦截它对旧 `dist/*.exe` 的删除（报 trash 失败、EXIT=1）。解决：先把旧 exe `mv` 改名挪开，再 `pyinstaller xxx.spec`，不要直接删。
- **瘦身**：剔除 `opencv_videoio_ffmpeg*_64.dll`（约 30MB，仅视频用，OCR 用不到）。在两个 spec 的 `Analysis` 之后：
  ```python
  a.binaries = [b for b in a.binaries if 'opencv_videoio_ffmpeg' not in b[0]]
  a.datas    = [d for d in a.datas    if 'opencv_videoio_ffmpeg' not in d[0]]
  ```
- Qt 精简：用 PyInstaller 自带 PyQt5 hook（`hiddenimports` 列 QtWidgets/QtCore/QtGui/QtSvg/sip 即可），**不要** `collect_all('PyQt5')`，并在 `excludes` 里列出未用的 Qt 模块（Qml/Quick/Network/PrintSupport/Multimedia/... 约 100MB），避免打进未用模块。
- 两个 spec 均 `console=False`、`--onefile`（EXE 节点无 COLLECT 即 one-file）。

---

## 9. 运行库分发（bat）

Win7 目标机首次运行前必须装运行库。随 dist 附带且离线可用：
- `vc_redist.x64.exe`（Visual C++ 2015–2022 运行库，提供 vcruntime140 + 整套 UCRT）
- `Windows6.1-KB2999226-x64.msu`（UCRT 基础补丁）
- `Windows6.1-KB3118401-x64.msu`（UCRT 补充补丁）
- （另附 x86 MSU 与 `WindowsUCRT.zip` 作 32 位/极端情况备用）

bat 用 **GBK 编码（无 BOM）**，否则 Win7 cmd 中文乱码。内容顺序：自动提权 → `vc_redist.x64.exe /install /quiet /norestart` → `wusa KB2999226 /quiet /norestart` → `wusa KB3118401 /quiet /norestart` → 提示重启。生成脚本见 `scripts/make_bat.py`。

> 若用户机器已装好 VC++ 2015-2022 运行库（多数 Win7 已满足），可直接双击 EXE 无需跑 bat。但文档仍建议先跑一次 bat 最稳妥。

---

## 10. 验证方法（沙箱无 GUI）

1. **离屏启动存活检测**：
   ```bash
   QT_QPA_PLATFORM=offscreen python main.py & PID=$!
   sleep 10
   kill -0 $PID && echo ALIVE   # ALIVE = 启动无崩溃
   ```
2. **扫描 exe 内 DLL 依赖路径**（确认根因是否根除）：用 `CArchiveReader` 遍历成员搜 `b"api-ms-win-core-path"`（见第 2、3 节）。
3. **确认 vcruntime 版本打入**：检查打包后 exe 顶层 `VCRUNTIME140.dll` 字节数应为 2025 版（约 124544 字节），而非 2021 旧版。
4. scanner.py 纯逻辑可在离屏下单独跑单元验证（无界面依赖）。
