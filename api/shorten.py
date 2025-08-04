"""
Vercel Function for sv.link batch URL shortening
"""

import json
import requests
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
        """Handle POST requests for URL shortening"""
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            api_key = data.get('api_key')
            urls = data.get('urls', [])
            
            # Validate input
            if not api_key:
                self.send_error_response({'error': '缺少 API Key'}, 400)
                return
            
            if not urls:
                self.send_error_response({'error': '缺少網址清單'}, 400)
                return
            
            # Process URLs
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
            
            # Send success response
            success_count = sum(1 for r in results if r['success'])
            
            response_data = {
                'results': results,
                'summary': {
                    'total': len(results),
                    'success': success_count,
                    'failed': len(results) - success_count
                }
            }
            
            self.send_success_response(response_data)
            
        except json.JSONDecodeError:
            self.send_error_response({'error': 'JSON 格式錯誤'}, 400)
        except Exception as e:
            self.send_error_response({'error': f'伺服器錯誤: {str(e)}'}, 500)

    def do_GET(self):
        """Handle GET requests"""
        self.send_error_response({'error': '只支援 POST 請求'}, 405)

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