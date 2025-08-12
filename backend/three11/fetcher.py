"""
311 Data Fetcher

Handles fetching data from 311 API endpoints.
"""

import requests
import zipfile
import io

def fetch_data_from_endpoint(endpoint: str):
    """Fetch data from an API endpoint."""
    print(f"Fetching data from: {endpoint}")
    
    try:
        response = requests.get(endpoint, timeout=30)
        response.raise_for_status()
        
        # Check if it's a ZIP file
        if endpoint.endswith('.zip') or 'application/zip' in response.headers.get('Content-Type', ''):
            print("Detected ZIP file, extracting CSV data...")
            return extract_zip_data(response.content)
        
        return response.text
        
    except Exception as e:
        print(f"Error fetching from endpoint: {e}")
        return None

def extract_zip_data(zip_content: bytes):
    """Extract CSV data from ZIP file."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            # Look for CSV files in the ZIP
            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
            
            if not csv_files:
                print("No CSV files found in ZIP")
                return None
            
            # Use the first CSV file
            csv_filename = csv_files[0]
            print(f"Extracting data from {csv_filename}")
            
            with zip_file.open(csv_filename) as csv_file:
                csv_content_bytes = csv_file.read()
                
                # Try different encodings
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                csv_content = None
                
                for encoding in encodings:
                    try:
                        csv_content = csv_content_bytes.decode(encoding)
                        print(f"Successfully decoded with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if csv_content is None:
                    print("Failed to decode CSV with any encoding")
                    return None
                
                return csv_content
                
    except Exception as e:
        print(f"Error extracting ZIP data: {e}")
        return None
