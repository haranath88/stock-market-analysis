import requests, zipfile, io, os, datetime, json

BASE = r"D:\Stock Market Analysis"
HISTORY = os.path.join(BASE, "Stock_History")
os.makedirs(HISTORY, exist_ok=True)

def download_for_date(date_str):
    # date_str = "19-Oct-2026" format NSE expects
    print(f"Trying NSE API for {date_str}")
    
    # Your API link format
    api_url = f"https://www.nseindia.com/api/reports?archives=%5B%7B%22name%22%3A%22Full%20Bhavcopy%20and%20Security%20Deliverable%20data%22%2C%22type%22%3A%22daily-reports%22%2C%22category%22%3A%22capital-market%22%2C%22section%22%3A%22equities%22%7D%5D&date={date_str}&type=equities&mode=single"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/all-reports"
    }
    
    session = requests.Session()
    try:
        # Step 1: Get NSE main page to get cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=20)
        r = session.get(api_url, headers=headers, timeout=20)
        print(f"API Status: {r.status_code}")
        print(r.text[:500])
        
        data = r.json()
        # data usually contains list of files
        if isinstance(data, dict) and 'data' in data:
            # Try to find CSV URL
            for item in data.get('data', []):
                if isinstance(item, dict):
                    file_url = item.get('fileUrl') or item.get('link') or item.get('url')
                    if file_url:
                        print(f"Found file: {file_url}")
                        return download_file(file_url, date_str, session)
        
        # Fallback: Try new archive format (2024+)
        dt = datetime.datetime.strptime(date_str, "%d-%b-%Y")
        yyyymmdd = dt.strftime("%Y%m%d")
        fallback_url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip"
        print(f"Trying fallback URL: {fallback_url}")
        return download_file(fallback_url, date_str, session)
        
    except Exception as e:
        print(f"Error: {e}")
        # Try fallback directly
        dt = datetime.datetime.strptime(date_str, "%d-%b-%Y")
        yyyymmdd = dt.strftime("%Y%m%d")
        fallback_url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip"
        return download_file(fallback_url, date_str, session)

def download_file(url, date_str, session):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = session.get(url, headers=headers, timeout=30)
        if r.status_code == 200 and len(r.content) > 1000:
            # Check if zip
            if url.endswith(".zip"):
                z = zipfile.ZipFile(io.BytesIO(r.content))
                csv_name = z.namelist()[0]
                content = z.read(csv_name)
            else:
                content = r.content
            
            # Save to Stock_History
            safe_name = f"BhavCopy_{date_str.replace('-','_')}.csv"
            save_path = os.path.join(HISTORY, safe_name)
            with open(save_path, "wb") as f:
                f.write(content)
            print(f"SAVED: {save_path} | Size: {len(content)//1024} KB")
            # Also save as bhavcopy.csv for your scripts
            with open(os.path.join(BASE, "bhavcopy.csv"), "wb") as f:
                f.write(content)
            return True
        else:
            print(f"Failed download {url} Status {r.status_code}")
            return False
    except Exception as e:
        print(f"Download error {e}")
        return False

if __name__ == "__main__":
    today = datetime.datetime.now()
    # If today is weekend, try Friday
    dates_to_try = []
    for i in range(5):
        d = today - datetime.timedelta(days=i)
        if d.weekday() < 5: # Mon-Fri
            dates_to_try.append(d.strftime("%d-%b-%Y"))
    
    for ds in dates_to_try:
        if download_for_date(ds):
            break