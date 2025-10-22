@echo off
REM ==============================================
REM  ジョイマン百人一首 Streamlitアプリ 起動スクリプト
REM  同じフォルダに app.py と Excel を置いてください
REM ==============================================

setlocal

REM === Python環境チェック ===
where python >nul 2>nul
if errorlevel 1 (
    echo [エラー] Pythonが見つかりません。
    echo Pythonをインストールし、環境変数PATHに追加してください。
    pause
    exit /b
)

REM === カレントディレクトリをこのbatファイルの場所に変更 ===
cd /d "%~dp0"

echo ----------------------------------------------
echo  Let's Joyman !!
echo ----------------------------------------------

REM === Streamlitを起動 ===
python -m streamlit run app.py

echo ----------------------------------------------
echo  Thank you.
echo ----------------------------------------------
pause
