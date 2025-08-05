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
    """匯出 CSV"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': '沒有可匯出的數據'}), 400
        
        # 使用 StringIO 生成 CSV 內容
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
        
        # 取得 CSV 字串內容
        csv_content = output.getvalue()
        output.close()
        
        # 添加 BOM 並編碼為 UTF-8
        csv_with_bom = '\ufeff' + csv_content
        csv_bytes = csv_with_bom.encode('utf-8')
        csv_base64 = base64.b64encode(csv_bytes).decode('ascii')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sv-link-results_{timestamp}.csv'
        
        return jsonify({
            'content': csv_base64,
            'filename': filename,
            'mimetype': 'text/csv;charset=utf-8',
            'size': len(csv_bytes),
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
        
        # 建立記憶體中的 ZIP 檔案
        zip_buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for index, result in enumerate(success_results, 1):
                    try:
                        short_url = result.get('short', '')
                        original_url = result.get('original', '')
                        
                        if not short_url or not short_url.startswith('http'):
                            continue
                        
                        # 生成簡單但可靠的 QR Code SVG
                        svg_content = generate_simple_qr_svg(short_url, index)
                        
                        # 生成檔案名稱
                        filename = generate_safe_filename(original_url, index)
                        
                        # 加入 SVG 檔案
                        zip_file.writestr(f"{filename}.svg", svg_content)
                        
                        # 加入對應的資訊檔案
                        info_content = f"原始網址: {original_url}\n短網址: {short_url}\n生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        zip_file.writestr(f"{filename}.txt", info_content)
                        
                    except Exception as e:
                        print(f"處理項目 {index} 時發生錯誤: {e}")
                        continue
                
                # 加入摘要檔案
                summary_content = f"""StreetVoice sv.link QR Code 批次生成摘要

生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
總共處理: {len(success_results)} 個短網址
檔案格式: SVG

工具: StreetVoice sv.link 批次短網址生成器
"""
                zip_file.writestr("_summary.txt", summary_content)
                
        except Exception as e:
            return jsonify({'error': f'ZIP 檔案建立失敗: {str(e)}'}), 500
        
        # 檢查 ZIP 內容
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()
        
        if len(zip_content) < 100:  # ZIP 檔案太小表示可能有問題
            return jsonify({'error': 'ZIP 檔案生成異常，內容過小'}), 500
        
        # 編碼為 base64
        try:
            zip_base64 = base64.b64encode(zip_content).decode('ascii')
        except Exception as e:
            return jsonify({'error': f'Base64 編碼失敗: {str(e)}'}), 500
        
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

def generate_simple_qr_svg(url, index):
    """生成簡單可靠的 QR Code SVG"""
    try:
        # 使用基本的 qrcode 庫生成
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # 取得 QR Code 矩陣
        matrix = qr.modules
        size = len(matrix)
        
        # 手動生成 SVG
        cell_size = 10
        border = 4 * cell_size
        total_size = (size + 8) * cell_size
        
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_size}" height="{total_size}" viewBox="0 0 {total_size} {total_size}">',
            f'<rect width="{total_size}" height="{total_size}" fill="white"/>',
        ]
        
        # 繪製 QR Code 模組
        for row in range(size):
            for col in range(size):
                if matrix[row][col]:
                    x = (col + 4) * cell_size
                    y = (row + 4) * cell_size
                    svg_parts.append(f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="#FF6B6B"/>')
        
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)
        
    except Exception as e:
        # 備用方案：生成純文字 SVG
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <rect width="200" height="200" fill="white" stroke="#ccc"/>
    <text x="100" y="90" text-anchor="middle" font-family="Arial" font-size="14" fill="#FF6B6B">QR Code #{index}</text>
    <text x="100" y="110" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">{url[:25]}...</text>
    <text x="100" y="130" text-anchor="middle" font-family="Arial" font-size="8" fill="#999">生成失敗，請手動建立</text>
</svg>"""

def generate_safe_filename(url, index):
    """生成安全的檔案名稱"""
    try:
        # 嘗試從 URL 提取有意義的部分
        if 'streetvoice.com/' in url:
            # StreetVoice 網址處理
            parts = url.split('streetvoice.com/')
            if len(parts) > 1:
                path_part = parts[1].split('/')[0].split('?')[0]
                if path_part:
                    # 清理檔名，只保留安全字符
                    safe_name = re.sub(r'[^\w\-_\.]', '', path_part)
                    if safe_name:
                        return f"sv_{safe_name}"
        
        # 其他網址處理
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').replace('.', '_')
        path = parsed.path.strip('/').replace('/', '_')
        
        if path:
            safe_path = re.sub(r'[^\w\-_\.]', '', path)[:20]  # 限制長度
            if safe_path:
                return f"{domain}_{safe_path}"
        
        return f"{domain}_link"
    
    except:
        pass
    
    # 預設檔名
    return f"qrcode_{index:03d}"

if __name__ == '__main__':
    # Render 會設定 PORT 環境變數
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)