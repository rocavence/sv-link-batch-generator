"""
Vercel Function for CSV export
"""

import json
import csv
import io
import base64
from datetime import datetime
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handle POST requests for CSV export"""
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            results = data.get('results', [])
            
            if not results:
                self.send_error_response({'error': '沒有可匯出的數據'}, 400)
                return
            
            # Generate CSV content
            csv_content = self.generate_csv(results)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'sv-link-results_{timestamp}.csv'
            
            # Encode content to base64
            csv_base64 = base64.b64encode(csv_content.encode('utf-8-sig')).decode()
            
            response_data = {
                'content': csv_base64,
                'filename': filename,
                'mimetype': 'text/csv;charset=utf-8;',
                'size': len(csv_content),
                'encoding': 'base64'
            }
            
            self.send_success_response(response_data)
            
        except json.JSONDecodeError:
            self.send_error_response({'error': 'JSON 格式錯誤'}, 400)
        except Exception as e:
            self.send_error_response({'error': f'匯出失敗: {str(e)}'}, 500)

    def generate_csv(self, results):
        """Generate CSV content from results"""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write header
        header = ['序號', '原始網址', '短網址', '狀態', '處理時間']
        writer.writerow(header)
        
        # Generate timestamp
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Write data rows
        for index, result in enumerate(results, 1):
            original_url = result.get('original', '未知')
            short_url = result.get('short', '生成失敗')
            success = result.get('success', False)
            status = '成功' if success else '失敗'
            
            writer.writerow([
                index,
                original_url,
                short_url,
                status,
                export_time
            ])
        
        # Add summary
        total_count = len(results)
        success_count = sum(1 for r in results if r.get('success', False))
        failed_count = total_count - success_count
        
        writer.writerow([])
        writer.writerow(['=== 處理摘要 ==='])
        writer.writerow(['總數量', total_count])
        writer.writerow(['成功數量', success_count])
        writer.writerow(['失敗數量', failed_count])
        writer.writerow(['成功率', f'{(success_count/total_count*100):.1f}%'])
        writer.writerow(['匯出時間', export_time])
        writer.writerow(['工具', 'StreetVoice sv.link 批次短網址生成器'])
        
        csv_content = output.getvalue()
        output.close()
        return csv_content

    def send_success_response(self, data):
        """Send successful JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def send_error_response(self, data, status_code):
        """Send error JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))