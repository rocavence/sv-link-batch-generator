"""
StreetVoice sv.link 批次短網址生成器 - Render 版本
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import csv
import io
import base64
import qrcode
import zipfile
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """主頁面"""
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """靜態檔案服務"""
    return send_from_directory('static', filename)

@app.route('/api/shorten', methods=['POST', 'OPTIONS'])
def shorten_urls():
    """批次短網址生成 API"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        urls = data.get('urls', [])
        
        if not api_key:
            return jsonify({'error': '缺少 API Key'}), 400
        
        if not urls:
            return jsonify({'error': '缺少網址清單'}), 400
        
        results = []
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            try:
                response = requests.post(
                    'https://sv.link/api/v2/links',
                    headers={
                        'Content-Type': 'application/json',
                        'X-API-Key': api_key
                    },
                    json={
                        'target': url,
                        'domain': 'sv.link'
                    },
                    timeout=15
                )
                
                if response.status_code == 201:
                    data = response.json()
                    short_url = data.get('shortUrl') or data.get('link') or data.get('id')
                    
                    if short_url and not short_url.startswith('http'):
                        short_url = f"https://{short_url}"
                    
                    results.append({
                        'original': url,
                        'short': short_url,
                        'success': True
                    })
                else:
                    results.append({
                        'original': url,
                        'short': f'HTTP {response.status_code} 錯誤',
                        'success': False
                    })
                    
            except requests.exceptions.RequestException as e:
                results.append({
                    'original': url,
                    'short': f'請求錯誤: {str(e)[:50]}',
                    'success': False
                })
            except Exception as e:
                results.append({
                    'original': url,
                    'short': f'未知錯誤: {str(e)[:50]}',
                    'success': False
                })
        
        success_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            'results': results,
            'summary': {
                'total': len(results),
                'success': success_count,
                'failed': len(results) - success_count
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'伺服器錯誤: {str(e)}'}), 500

@app.route('/api/export/csv', methods=['POST', 'OPTIONS'])
def export_csv():
    """匯出 CSV - 英文版本"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': 'No data to export'}), 400
        
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        writer.writerow(['No', 'Original URL', 'Short URL', 'Status', 'Process Time'])
        
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for index, result in enumerate(results, 1):
            writer.writerow([
                index,
                result.get('original', ''),
                result.get('short', ''),
                'Success' if result.get('success', False) else 'Failed',
                export_time
            ])
        
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('success', False))
        
        writer.writerow([])
        writer.writerow(['=== Summary ==='])
        writer.writerow(['Total', total_count])
        writer.writerow(['Success', success_count])
        writer.writerow(['Failed', total_count - success_count])
        writer.writerow(['Success Rate', f'{(success_count/total_count*100):.1f}%'])
        writer.writerow(['Export Time', export_time])
        writer.writerow(['Tool', 'StreetVoice sv.link Batch Generator'])
        
        csv_content = output.getvalue()
        output.close()
        
        csv_bytes = csv_content.encode('utf-8')
        csv_base64 = base64.b64encode(csv_bytes).decode('ascii')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sv-link-results_{timestamp}.csv'
        
        return jsonify({
            'content': csv_base64,
            'filename': filename,
            'mimetype': 'text/csv',
            'size': len(csv_bytes),
            'encoding': 'base64'
        })
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/qr/zip', methods=['POST', 'OPTIONS'])
def export_qr_zip():
    """批次生成 QR Code ZIP - 使用暫存檔案"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        success_results = [r for r in results if r.get('success', False) and r.get('short')]
        
        if not success_results:
            return jsonify({'error': '沒有成功的短網址可生成 QR Code'}), 400
        
        # 建立暫存目錄
        temp_dir = f"/tmp/qr_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_files = []
        
        try:
            # 步驟 1: 批次生成 SVG 檔案並暫存到磁碟
            for index, result in enumerate(success_results, 1):
                short_url = result.get('short', '')
                
                if not short_url:
                    continue
                
                try:
                    # 生成 QR Code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(short_url)
                    qr.make(fit=True)
                    
                    # 生成 SVG 內容
                    svg_content = generate_qr_svg(qr, short_url, index)
                    
                    # 暫存到磁碟
                    temp_filename = os.path.join(temp_dir, f"qrcode_{index:03d}.svg")
                    with open(temp_filename, 'w', encoding='utf-8') as f:
                        f.write(svg_content)
                    
                    temp_files.append(temp_filename)
                    
                except Exception as e:
                    print(f"生成 QR Code {index} 失敗: {e}")
                    continue
            
            if not temp_files:
                return jsonify({'error': '沒有成功生成任何 QR Code'}), 500
            
            # 步驟 2: 將暫存檔案打包成 ZIP
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f"/tmp/sv-link-qrcodes_{timestamp}.zip"
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
                for temp_file in temp_files:
                    # 取得檔案名稱（不含路徑）
                    arc_name = os.path.basename(temp_file)
                    zf.write(temp_file, arc_name)
            
            # 讀取 ZIP 檔案內容
            with open(zip_filename, 'rb') as f:
                zip_content = f.read()
            
            # Base64 編碼
            zip_base64 = base64.b64encode(zip_content).decode('ascii')
            
            # 步驟 3: 刪除暫存檔案
            cleanup_temp_files(temp_files, temp_dir)
            
            # 步驟 4: 設定 ZIP 檔案 30 分鐘後自動清理
            schedule_zip_cleanup(zip_filename, 30 * 60)  # 30 分鐘
            
            return jsonify({
                'content': zip_base64,
                'filename': f'sv-link-qrcodes_{timestamp}.zip',
                'mimetype': 'application/zip',
                'size': len(zip_content),
                'encoding': 'base64'
            })
            
        except Exception as e:
            # 發生錯誤時清理暫存檔案
            cleanup_temp_files(temp_files, temp_dir)
            return jsonify({'error': f'ZIP 生成失敗: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'處理失敗: {str(e)}'}), 500

def cleanup_temp_files(temp_files, temp_dir):
    """清理暫存檔案和目錄"""
    try:
        # 刪除暫存檔案
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        # 刪除暫存目錄
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
            
    except Exception as e:
        print(f"清理暫存檔案失敗: {e}")

def schedule_zip_cleanup(zip_filename, delay_seconds):
    """安排 ZIP 檔案延遲清理"""
    import threading
    import time
    
    def cleanup_zip():
        try:
            time.sleep(delay_seconds)
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
                print(f"已清理 ZIP 檔案: {zip_filename}")
        except Exception as e:
            print(f"清理 ZIP 檔案失敗: {e}")
    
    # 在背景執行緒中執行清理
    cleanup_thread = threading.Thread(target=cleanup_zip, daemon=True)
    cleanup_thread.start()

def generate_qr_svg(qr, url, index):
    """生成 QR Code SVG"""
    try:
        matrix = qr.modules
        size = len(matrix)
        
        cell_size = 10
        border = 4 * cell_size
        total_size = (size + 8) * cell_size
        
        svg_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_size}" height="{total_size}" viewBox="0 0 {total_size} {total_size}">',
            f'<rect width="{total_size}" height="{total_size}" fill="white"/>',
        ]
        
        for row in range(size):
            for col in range(size):
                if matrix[row][col]:
                    x = (col + 4) * cell_size
                    y = (row + 4) * cell_size
                    svg_lines.append(f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="#FF6B6B"/>')
        
        svg_lines.extend([
            f'<!-- QR Code #{index} -->',
            f'<!-- URL: {url} -->',
            '</svg>'
        ])
        
        return '\n'.join(svg_lines)
        
    except Exception as e:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <rect width="200" height="200" fill="white" stroke="#ccc"/>
    <text x="100" y="100" text-anchor="middle" font-family="Arial" font-size="12" fill="#FF6B6B">QR Code #{index}</text>
    <text x="100" y="120" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">Generation failed</text>
</svg>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)