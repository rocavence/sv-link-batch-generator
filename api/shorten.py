"""
Vercel Function for sv.link batch URL shortening
"""

import json
import requests


def handler(request):
    """Main handler function for Vercel"""
    
    # Handle CORS for all requests
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS request
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Only allow POST
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': '只支援 POST 請求'})
        }
    
    try:
        # Parse request body
        if hasattr(request, 'get_json'):
            data = request.get_json()
        else:
            # Fallback for different request formats
            body = request.data if hasattr(request, 'data') else request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
        
        api_key = data.get('api_key')
        urls = data.get('urls', [])
        
        # Validate input
        if not api_key:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '缺少 API Key'})
            }
        
        if not urls:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '缺少網址清單'})
            }
        
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
                    response_data = response.json()
                    short_url = response_data.get('shortUrl') or response_data.get('link') or response_data.get('id')
                    
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
        
        # Return results
        success_count = sum(1 for r in results if r['success'])
        
        response_body = {
            'results': results,
            'summary': {
                'total': len(results),
                'success': success_count,
                'failed': len(results) - success_count
            }
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body, ensure_ascii=False)
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'JSON 格式錯誤'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'伺服器錯誤: {str(e)}'})
        }