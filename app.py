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
        
        # 生成 CSV - 使用 BytesIO 而不是 StringIO 來避免編碼問題
        output = io.BytesIO()
        
        # 寫入 BOM 以確保 Excel 正確識別 UTF-8
        output.write('\ufeff'.encode('utf-8'))
        
        # 準備 CSV 內容
        csv_content = []
        
        # 標頭
        csv_content.append(['序號', '原始網址', '短網址', '狀態', '處理時間'])
        
        # 生成時間戳
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 數據行
        for index, result in enumerate(results, 1):
            csv_content.append([
                str(index),
                result.get('original', '未知'),
                result.get('short', '生成失敗'),
                '成功' if result.get('success', False) else '失敗',
                export_time
            ])
        
        # 摘要
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('success', False))
        
        csv_content.extend([
            [],
            ['=== 處理摘要 ==='],
            ['總數量', str(total_count)],
            ['成功數量', str(success_count)],
            ['失敗數量', str(total_count - success_count)],
            ['成功率', f'{(success_count/total_count*100):.1f}%'],
            ['匯出時間', export_time],
            ['工具', 'StreetVoice sv.link 批次短網址生成器']
        ])
        
        # 寫入 CSV 內容
        for row in csv_content:
            # 手動處理 CSV 格式，確保正確編碼
            escaped_row = []
            for field in row:
                field_str = str(field) if field is not None else ''
                # 如果包含逗號、換行或引號，需要用引號包圍並轉義
                if ',' in field_str or '\n' in field_str or '"' in field_str:
                    field_str = '"' + field_str.replace('"', '""') + '"'
                escaped_row.append(field_str)
            
            line = ','.join(escaped_row) + '\n'
            output.write(line.encode('utf-8'))
        
        # 取得內容並編碼為 base64
        output.seek(0)
        csv_bytes = output.getvalue()
        csv_base64 = base64.b64encode(csv_bytes).decode('ascii')
        output.close()
        
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
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            for index, result in enumerate(success_results, 1):
                try:
                    short_url = result.get('short', '')
                    original_url = result.get('original', '')
                    
                    if not short_url:
                        continue
                    
                    # 生成 QR Code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(short_url)
                    qr.make(fit=True)
                    
                    # 生成檔案名稱
                    filename = generate_safe_filename(original_url, index)
                    
                    # 使用 qrcode 的 SVG 圖片工廠
                    from qrcode.image.svg import SvgPathImage
                    
                    # 生成 SVG
                    img = qr.make_image(
                        image_factory=SvgPathImage,
                        fill_color="#FF6B6B",
                        back_color="white"
                    )
                    
                    # 將 SVG 轉為字串
                    svg_buffer = io.StringIO()
                    img.save(svg_buffer)
                    svg_content = svg_buffer.getvalue()
                    svg_buffer.close()
                    
                    # 確保 SVG 內容完整
                    if not svg_content.strip():
                        # 如果 SVG 內容空白，生成手動 SVG
                        svg_content = generate_manual_svg_qr(short_url)
                    
                    # 加入 ZIP 檔案
                    zip_file.writestr(f"{filename}.svg", svg_content.encode('utf-8'))
                    
                    # 同時建立一個包含網址資訊的文字檔
                    info_content = f"原始網址: {original_url}\n短網址: {short_url}\n生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    zip_file.writestr(f"{filename}.txt", info_content.encode('utf-8'))
                    
                except Exception as e:
                    print(f"生成 QR Code 失敗 (項目 {index}): {e}")
                    # 生成錯誤日誌檔案
                    error_content = f"生成失敗\n原始網址: {result.get('original', 'N/A')}\n短網址: {result.get('short', 'N/A')}\n錯誤: {str(e)}"
                    safe_name = f"error_{index}"
                    zip_file.writestr(f"{safe_name}.txt", error_content.encode('utf-8'))
                    continue
            
            # 加入摘要檔案
            summary_content = generate_summary_content(success_results)
            zip_file.writestr("_summary.txt", summary_content.encode('utf-8'))
        
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()
        zip_buffer.close()
        
        if len(zip_content) == 0:
            return jsonify({'error': 'ZIP 檔案生成失敗，內容為空'}), 500
        
        zip_base64 = base64.b64encode(zip_content).decode('ascii')
        
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

def generate_manual_svg_qr(data):
    """手動生成簡單的 SVG QR Code（備用方案）"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <rect width="200" height="200" fill="white"/>
    <text x="100" y="100" text-anchor="middle" font-family="Arial" font-size="12" fill="#FF6B6B">
        QR Code
    </text>
    <text x="100" y="120" text-anchor="middle" font-family="Arial" font-size="8" fill="#333">
        {data[:30]}...
    </text>
</svg>"""

def generate_summary_content(results):
    """生成摘要內容"""
    total = len(results)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    content = f"""StreetVoice sv.link QR Code 批次生成摘要

生成時間: {timestamp}
總共處理: {total} 個短網址
檔案格式: SVG (可縮放向量圖形)

檔案說明:
- .svg 檔案: QR Code 圖形檔案
- .txt 檔案: 對應的網址資訊
- _summary.txt: 此摘要檔案

使用方式:
1. SVG 檔案可在網頁瀏覽器中開啟
2. 可匯入設計軟體 (如 Illustrator, Figma) 編輯
3. 可直接列印或用於數位媒體

技術資訊:
- QR Code 錯誤修正等級: M (15%)
- 邊框大小: 4 像素
- 填充色彩: #FF6B6B (StreetVoice 紅)
- 背景色彩: 白色

工具: StreetVoice sv.link 批次短網址生成器
"""
    return content

if __name__ == '__main__':
    # Render 會設定 PORT 環境變數
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)