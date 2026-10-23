@echo off
REM Starts the unified LS_Pycro_App code (unify-microscopes branch) on Willamette.
REM Uses the Python environment (venv) of the existing installation; the old folder is not modified.
cd /d "C:\Users\Will LSM\Desktop\Microscope Software\LS_Pycro_App_unified\LS_Pycro_App"
"C:\Users\Will LSM\Desktop\Microscope Software\LS_Pycro_App\venv\Scripts\python.exe" app_start.py
pause
