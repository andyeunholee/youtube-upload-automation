@echo off
echo Starting YouTube Auto Uploader...
cd /d "h:\My Drive\Automation-H\AntiGravity\Youtube_Auto"
call .venv\Scripts\activate
streamlit run app.py
pause
