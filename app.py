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
import re

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
                # 呼叫 sv.link API
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
    """匯出 CSV - 最簡化版本"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': '沒有可匯出的數據'}), 400
        
        # 建立 CSV 內容（純文字）
        lines = []
        lines.append("序號,原始網址,短網址,狀態,處理時間")
        
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for index, result in enumerate(results, 1):
            original = result.get('original', '').replace(',', '，')  # 替換逗號避免CSV問題
            short = result.get('short', '').replace(',', '，')
            status = '成功' if result.get('success', False) else '失敗'
            
            line = f"{index},{original},{short},{status},{export_time}"
            lines.append(line)
        
        # 加入摘要
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('success', False))
        
        lines.append("")
        lines.append("=== 處理摘要 ===")
        lines.append(f"總數量,{total_count}")
        lines.append(f"成功數量,{success_count}")
        lines.append(f"失敗數量,{total_count - success_count}")
        lines.append(f"成功率,{(success_count/total_count*100):.1f}%")
        lines.append(f"匯出時間,{export_time}")
        lines.append("工具,StreetVoice sv.link 批次短網址生成器")
        
        # 組合成完整 CSV 文字
        csv_text = "\n".join(lines)
        
        # 加上 BOM 並轉為 bytes
        csv_with_bom = "\ufeff" + csv_text
        csv_bytes = csv_with_bom.encode('utf-8')
        
        # Base64 編碼
        csv_base64 = base64.b64encode(csv_bytes).decode()
        
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
        return jsonify({'error': f'匯出失敗: {str(e)}'}), 500

@app.route('/api/qr/zip', methods=['POST', 'OPTIONS'])
def export_qr_zip():
    """生成 QR Code ZIP - 最簡化版本"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        success_results = [r for r in results if r.get('success', False)]
        
        if not success_results:
            return jsonify({'error': '沒有成功的短網址可生成 QR Code'}), 400
        
        # 建立記憶體中的 ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for index, result in enumerate(success_results, 1):
                short_url = result.get('short', '')
                original_url = result.get('original', '')
                
                if not short_url:
                    continue
                
                # 生成簡單的文字 QR Code（先測試文字檔案能否正常工作）
                qr_info = f"""QR Code #{index}

短網址: {short_url}
原始網址: {original_url}
生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

請使用 QR Code 生成器網站來建立實際的 QR Code：
1. 前往 https://www.qr-code-generator.com/
2. 輸入短網址: {short_url}
3. 下載 QR Code 圖片
"""
                
                filename = f"qr_{index:03d}"
                zf.writestr(f"{filename}.txt", qr_info.encode('utf-8'))
        
        zip_buffer.seek(0)
        zip_content = zip_buffer.read()
        
        # Base64 編碼
        zip_base64 = base64.b64encode(zip_content).decode()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sv-link-qrcodes_{timestamp}.zip'
        
        return jsonify({
            'content': zip_base64,
            'filename': filename,
            'mimetype': 'application/zip',
            'size': len(zip_content),
            'encoding': 'base64'
        })
        
    except Exception as e:
        return jsonify({'error': f'ZIP 生成失敗: {str(e)}'}), 500

if __name__ == '__main__':
    # Render 會設定 PORT 環境變數
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)