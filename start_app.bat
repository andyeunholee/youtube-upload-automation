@echo off
echo Starting YouTube Auto Uploader...
cd /d "g:\My Drive\Youtube_Auto"
call .venv\Scripts\activate
streamlit run app.py
pause
