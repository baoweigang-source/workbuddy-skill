# -*- coding: utf-8 -*-
"""
生成 Win7 运行库一键安装 bat（GBK 编码，无 BOM）。

为什么必须 GBK：Win7 的 cmd 默认代码页是 GBK(936)。若 bat 用 UTF-8 写中文，
在 Win7 cmd 下会乱码。故本脚本把内容以 GBK 编码写出。

用法：
    python make_bat.py [输出路径，默认 ./安装UCRT补丁_x64.bat]

bat 行为：自动请求管理员权限 → 装 VC++ 2015-2022 运行库(x64)
→ 装 KB2999226 → 装 KB3118401 → 提示重启。全部离线（依赖同目录附带文件）。
"""
import os
import sys

BAT_CONTENT = r'''@echo off
cd /d "%~dp0"

:: 自动请求管理员权限，未提权时自动提权
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   办公计算机终端保密检查系统  ——  Win7 运行库一键安装
echo.
echo   本目录的 Win7 版 EXE 已用 Python 3.8 构建，
echo   已不含 api-ms-win-core-path 依赖，启动崩溃已解决。
echo   本脚本仅用于安装 VC++ 运行库（提供 C 运行库）。
echo ============================================================
echo.

echo [1/3] 安装 Visual C++ 2015-2022 运行库 (x64) ...
"%~dp0vc_redist.x64.exe" /install /quiet /norestart
echo      exit code: %errorlevel%

echo [2/3] 安装 KB2999226 (UCRT 基础补丁) ...
wusa.exe "%~dp0Windows6.1-KB2999226-x64.msu" /quiet /norestart
echo      exit code: %errorlevel%

echo [3/3] 安装 KB3118401 (UCRT 补充补丁) ...
wusa.exe "%~dp0Windows6.1-KB3118401-x64.msu" /quiet /norestart
echo      exit code: %errorlevel%

echo.
echo ============================================================
echo   安装完成，请【重启电脑一次】，然后双击 EXE 即可使用。
echo ============================================================
echo.
echo   注：若已安装过 VC++ 运行库，第 1 步会提示已安装，属正常。
echo   注：Win7 上图片 OCR 因系统缺少 Win8+ API 会自动降级，
echo       仅按文件名命中，docx/xlsx/pptx/pdf 内容检查不受影响。
echo.
pause
'''


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "安装UCRT补丁_x64.bat"
    # 关键：以 GBK 编码写出，无 BOM，保证 Win7 cmd 中文不乱码
    with open(out, "w", encoding="gbk", newline="\r\n") as f:
        f.write(BAT_CONTENT)
    size = os.path.getsize(out)
    print(f"已生成（GBK 编码，{size} 字节）：{os.path.abspath(out)}")


if __name__ == "__main__":
    main()
