# -*- mode: python ; coding: utf-8 -*-
"""PyQt5（Qt5）打包配置 —— Windows 7 SP1（64/32 位）专用构建，使用 Python 3.8。

为何用 Python 3.8：Python 3.9 起 CPython 核心改用 PathCch 系列函数，
依赖 api-ms-win-core-path-l1-1-0.dll，而 Windows 7 无此 API 集（且微软 UCRT 补丁
KB2999226/KB3118401 也不含它），导致 3.9 打包的 EXE 在 Win7 必报“找不到该 DLL”。
Python 3.8 是【最后一个原生支持 Windows 7】的版本，根本不导入 api-ms-win-core-path，
因此在 Win7（装好 VC++ 2015-2022 运行库兜底 api-ms-win-crt-* 即可）可正常启动。

本构建【包含 OCR 引擎】（rapidocr_onnxruntime + onnxruntime）：python38.dll 本身不依赖
api-ms-win-core-path，故 EXE 在 Win7 上可正常启动（这正是换 3.8 要解决的启动崩溃）。
注意：onnxruntime 的 DLL 仍使用 Win8+ 的 api-ms-win-core-path API 集，因此【图片 OCR
在 Win7 上会自动降级（仅按文件名命中）】，docx/xlsx/pptx/pdf 内容提取不受影响；
在 Win8+ 上 OCR 可正常启用。Win8+ 完整版见 build_qt_win8.spec。
"""
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtSvg', 'PyQt5.sip',
    'rapidocr_onnxruntime',
]

# Qt 精简：依赖 PyInstaller 自带的 PyQt5 hook 仅打包必要 Qt 二进制 + qwindows 平台插件，
# 不再 collect_all('PyQt5')，避免把 qml / translations / 网络 / 打印 / 多媒体等未用模块（约 100MB）打进 EXE。

# 图片 OCR 引擎（RapidOCR + onnxruntime，纯 Python，自带中文识别模型）
for _m in ('rapidocr_onnxruntime', 'onnxruntime'):
    try:
        _ret = collect_all(_m)
        datas += _ret[0]
        binaries += _ret[1]
        hiddenimports += _ret[2]
    except Exception:
        pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'webview', 'clr', 'clr_loader', 'pythonnet', 'PyQtWebEngine',
        # 未使用的 Qt 模块（精简体积，避免被 hook 顺带收集）
        'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtQuickWidgets', 'PyQt5.QtQuick3D',
        'PyQt5.QtNetwork', 'PyQt5.QtNetworkAuth', 'PyQt5.QtPrintSupport',
        'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets', 'PyQt5.QtOpenGL',
        'PyQt5.QtOpenGLWidgets', 'PyQt5.QtXml', 'PyQt5.QtXmlPatterns', 'PyQt5.QtSql',
        'PyQt5.QtTest', 'PyQt5.QtDesigner', 'PyQt5.QtHelp', 'PyQt5.QtUiTools',
        'PyQt5.Qt3DCore', 'PyQt5.Qt3DRender', 'PyQt5.Qt3DInput', 'PyQt5.Qt3DLogic',
        'PyQt5.Qt3DAnimation', 'PyQt5.Qt3DExtras', 'PyQt5.QtCharts',
        'PyQt5.QtDataVisualization', 'PyQt5.QtScxml', 'PyQt5.QtGamepad',
        'PyQt5.QtWebView', 'PyQt5.QtLocation', 'PyQt5.QtPositioning',
        'PyQt5.QtSensors', 'PyQt5.QtSerialPort', 'PyQt5.QtSerialBus',
        'PyQt5.QtTextToSpeech', 'PyQt5.QtRemoteObjects', 'PyQt5.QtNfc',
        'PyQt5.QtBluetooth', 'PyQt5.QtMacExtras', 'PyQt5.QtWinExtras',
        'PyQt5.QtX11Extras', 'PyQt5.QtAndroidExtras', 'PyQt5.QtScript',
        'PyQt5.QtScriptTools', 'PyQt5.QAxContainer', 'PyQt5.Qsci', 'PyQt5.uic',
    ],
    noarchive=False,
    optimize=0,
)

# 精简：opencv 的 ffmpeg 视频后端 dll（opencv_videoio_ffmpeg*_64.dll，约 30MB）
# 仅用于读取/写入视频文件，本工具的 RapidOCR 只做 cv2.imread/cvtColor/resize 等图像操作，
# 完全用不到视频后端。剔除后 import cv2 与 imread/imwrite 均正常，单 exe 约节省 30MB。
a.binaries = [b for b in a.binaries if 'opencv_videoio_ffmpeg' not in b[0]]
a.datas = [d for d in a.datas if 'opencv_videoio_ffmpeg' not in d[0]]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='办公计算机终端保密检查系统_Win7',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
