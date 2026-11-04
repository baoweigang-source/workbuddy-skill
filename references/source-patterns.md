# 可复用源码模式（baojian-gui）

本文档提取 scanner.py / report.py 中可复用、且对“容错降级”“中文报表”等场景通用的代码模式。复用时按需摘取，不必照搬全文。

---

## 1. 图片 OCR 引擎懒加载 + 自动降级（scanner.py）

**痛点**：RapidOCR/onnxruntime 在某些环境（如 Win7 缺 `api-ms-win-core-path`、或没装 VC++ 运行库）无法加载。若直接在模块顶层 `import`，一旦失败整个程序崩。

**模式**：模块级缓存 + `try/except` 懒加载，失败即返回 `None`，上层退化为“仅文件名匹配”，**绝不影响其它扫描**。

```python
# 懒加载：OCR 引擎不可用（如缺 VC++ 运行库）时自动降级为「仅文件名匹配」，不影响其它扫描。
_OCR_ENGINE = None
_OCR_READY = None
_OCR_TIMEOUT = 8  # 单张图片 OCR 超时（秒）
_OCR_LOCK = threading.Lock()  # onnxruntime/RapidOCR 多线程并发不安全，串行推理

def _get_ocr_engine():
    """返回 RapidOCR 实例；首次尝试并缓存结果；不可用返回 None。"""
    global _OCR_ENGINE, _OCR_READY
    if _OCR_READY is not None:
        return _OCR_ENGINE
    try:
        from rapidocr_onnxruntime import RapidOCR  # 仅在需要时才 import
        _OCR_ENGINE = RapidOCR()
        _OCR_READY = True
    except Exception:
        _OCR_ENGINE = None
        _OCR_READY = False
    return _OCR_ENGINE

def ocr_image_text(fp):
    """对图片做 OCR，返回拼接文本；空串表示无文字或引擎不可用。"""
    engine = _get_ocr_engine()
    if engine is None:
        return ""                       # 降级：交给调用方走「仅文件名」分支
    try:
        with _OCR_LOCK:                 # 串行，避免 onnxruntime 并发崩溃
            result, _ = engine(fp)
        return "\n".join([line[1] for line in (result or [])])
    except Exception:
        return ""

def _ocr_with_timeout(fp, timeout=_OCR_TIMEOUT):
    """带超时的 OCR，避免单张大图卡死整轮扫描。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(ocr_image_text, fp)
        try:
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return ""
```

**调用方逻辑（命中判定）**：
```python
text = _ocr_with_timeout(fp) or ""
if not text:
    # 降级：仅按文件名命中（图内文字无法识别，但文件名若含密级词仍命中）
    content_locs = ["图片OCR"]
    content_reason = "OCR识别(引擎不可用,仅文件名匹配)"
else:
    content_locs = ["图片OCR"]
    content_reason = "OCR识别"
```

---

## 2. 中文 PDF 报表字体回退链（report.py）

**痛点**：reportlab 默认字体不含中文，直接写中文会导出空白/方块。中文系统字体路径各异，并非每台机器都有 simhei。

**模式**：按优先级逐个 `try` 注册，全部失败则回退到 reportlab 自带的 CID 中文字体 `STSong-Light`（无需外部字体文件）。注册一次后全局复用。

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

_FONT = None

def setup_cn_font():
    """注册中文字体，返回字体名。只注册一次。优先级：simhei → msyh → simsun → STSong-Light(CID)。"""
    global _FONT
    if _FONT:
        return _FONT
    candidates = [
        (r"C:\Windows\Fonts\simhei.ttf", {}),
        (r"C:\Windows\Fonts\msyh.ttc", {"subfontIndex": 0}),
        (r"C:\Windows\Fonts\simsun.ttc", {"subfontIndex": 0}),
    ]
    for path, kw in candidates:
        try:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont("CN", path, **kw))
                _FONT = "CN"
                return _FONT
        except Exception:
            continue
    # 兜底：reportlab 自带 CID 中文字体，无需外部文件
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        _FONT = "STSong-Light"
    except Exception:
        _FONT = "Helvetica"  # 最终兜底（中文会显示为方块，仅防崩）
    return _FONT

# 使用：所有 ParagraphStyle 的 fontName 都用 setup_cn_font() 的返回值
font = setup_cn_font()
style = ParagraphStyle("c", fontName=font, fontSize=9, leading=13)
```

> 打包进 EXE 后，`C:\Windows\Fonts\` 路径在目标机依旧有效（系统字体目录不变），回退链可正常工作。

---

## 3. 文件级并行扫描（scanner.py）

**模式**：线程池做文件级并行（利用多核），但 OCR 推理已在 `ocr_image_text` 内加锁串行（见第 1 节），两者不冲突。

```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
    futures = {ex.submit(scan_one_file, fp): fp for fp in file_list}
    for fut in concurrent.futures.as_completed(futures):
        try:
            result = fut.result()
            collect(result)
        except Exception as e:
            log_error(futures[fut], e)
```

要点：
- OCR 推理本身重 CPU 且非线程安全 → 锁串行；并行只放在“文件调度/IO/内容提取”外层。
- 单文件处理用 `try/except` 包裹，单个文件异常不应中断整轮扫描。

---

## 4. 扫描结果模型（建议）

每个文件扫描结果建议统一为结构化对象，便于 GUI 展示与 PDF 报表复用：

```python
{
  "path": str,
  "type": "docx|xlsx|pptx|pdf|image|txt|...",
  "hit": bool,                       # 是否命中涉密关键词/密级标识
  "content_locs": [str],             # 命中位置来源，如 ["图片OCR","正文"]
  "content_reason": str,             # 命中原因描述
  "keywords": [str],                 # 命中的关键词列表
  "error": str | None,               # 单文件处理异常信息
}
```

> 该模型让 scanner.py（纯逻辑）与 main.py（GUI）、report.py（PDF）解耦——scanner 只产出数据，GUI/报表各取所需。
