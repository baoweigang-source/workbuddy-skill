# -*- mode: python ; coding: utf-8 -*-
"""PyQt5（Qt5）打包配置 —— 面向 Windows 8 / 8.1 / 10 / 11（Python 3.13，速度更快）；Win7 请用 build_qt.spec（Python 3.9）。不依赖 WebView2。"""
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
# 完全用不到视频后端。已在两个 venv 中验证：移除该 dll 后 import cv2 与 imread/imwrite 均正常。
# 故在此剔除，单 exe 约节省 30MB。
a.binaries = [b for b in a.binaries if 'opencv_videoio_ffmpeg' not in b[0]]
a.datas = [d for d in a.datas if 'opencv_videoio_ffmpeg' not in d[0]]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='办公计算机终端保密检查系统_Win8以上',
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
