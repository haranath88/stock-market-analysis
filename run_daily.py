import subprocess, os
BASE = r"D:\Stock Market Analysis"
os.chdir(BASE)

print("STEP 1: Auto downloading bhavcopy from NSE...")
subprocess.run(["python", "auto_download_bhavcopy.py"])

print("\nSTEP 2: Running your existing logics...")
subprocess.run(["python", "consistent_gainers_52w.py"])
subprocess.run(["python", "create_7_filters.py"])
subprocess.run(["python", "build.py"])

print("\nDONE - Open http://localhost:8000")