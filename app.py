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
import tempfile
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
    """匯出 CSV"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': '沒有可匯出的數據'}), 400
        
        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # 寫入標頭
        writer.writerow(['序號', '原始網址', '短網址', '狀態', '處理時間'])
        
        # 生成時間戳
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 寫入數據
        for index, result in enumerate(results, 1):
            writer.writerow([
                index,
                result.get('original', '未知'),
                result.get('short', '生成失敗'),
                '成功' if result.get('success', False) else '失敗',
                export_time
            ])
        
        # 加入摘要
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('success', False))
        
        writer.writerow([])
        writer.writerow(['=== 處理摘要 ==='])
        writer.writerow(['總數量', total_count])
        writer.writerow(['成功數量', success_count])
        writer.writerow(['失敗數量', total_count - success_count])
        writer.writerow(['成功率', f'{(success_count/total_count*100):.1f}%'])
        writer.writerow(['匯出時間', export_time])
        writer.writerow(['工具', 'StreetVoice sv.link 批次短網址生成器'])
        
        csv_content = output.getvalue()
        output.close()
        
        # 編碼為 base64
        csv_base64 = base64.b64encode(csv_content.encode('utf-8-sig')).decode()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sv-link-results_{timestamp}.csv'
        
        return jsonify({
            'content': csv_base64,
            'filename': filename,
            'mimetype': 'text/csv;charset=utf-8;',
            'size': len(csv_content),
            'encoding': 'base64'
        })
        
    except Exception as e:
        return jsonify({'error': f'匯出失敗: {str(e)}'}), 500

@app.route('/api/qr/zip', methods=['POST', 'OPTIONS'])
def export_qr_zip():
    """生成 QR Code ZIP"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        success_results = [r for r in results if r.get('success', False)]
        
        if not success_results:
            return jsonify({'error': '沒有成功的短網址可生成 QR Code'}), 400
        
        # 建立臨時 ZIP 檔案
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in success_results:
                try:
                    # 生成 QR Code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(result['short'])
                    qr.make(fit=True)
                    
                    # 生成 SVG
                    import qrcode.image.svg
                    factory = qrcode.image.svg.SvgPathImage
                    img = qr.make_image(image_factory=factory, fill_color="#FF6B6B", back_color="white")
                    
                    # 生成檔案名稱
                    original_url = result['original']
                    if 'streetvoice.com/' in original_url:
                        filename = original_url.split('streetvoice.com/')[-1].split('/')[0]
                        filename = ''.join(c for c in filename if c.isalnum() or c in '-_')
                    else:
                        filename = f"url_{len(zip_file.namelist()) + 1}"
                    
                    # 轉換 SVG 為字串
                    svg_io = io.StringIO()
                    img.save(svg_io)
                    svg_content = svg_io.getvalue()
                    
                    # 加入 ZIP
                    zip_file.writestr(f"{filename}.svg", svg_content)
                    
                except Exception as e:
                    print(f"生成 QR Code 失敗: {e}")
                    continue
        
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()
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
        return jsonify({'error': f'QR Code 生成失敗: {str(e)}'}), 500

if __name__ == '__main__':
    # Render 會設定 PORT 環境變數
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)