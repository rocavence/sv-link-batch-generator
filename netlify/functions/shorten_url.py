"""
StreetVoice sv.link 批次短網址生成 API
Netlify Function for URL shortening via sv.link API
"""

import json
import requests
import time


def handler(event, context):
    """
    Netlify Function handler for batch URL shortening
    """
    # CORS headers for cross-origin requests
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight OPTIONS request
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Only allow POST requests
    if event['httpMethod'] != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({
                'error': '只允許 POST 請求',
                'allowed_methods': ['POST']
            })
        }
    
    try:
        # Parse request body
        if not event.get('body'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '請求內容不能為空'})
            }
        
        body = json.loads(event['body'])
        api_key = body.get('api_key')
        urls = body.get('urls', [])
        
        # Validate input parameters
        if not api_key or not isinstance(api_key, str) or len(api_key.strip()) == 0:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '缺少有效的 API Key'})
            }
        
        if not urls or not isinstance(urls, list) or len(urls) == 0:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '缺少網址清單或格式錯誤'})
            }
        
        # Clean and validate URLs
        cleaned_urls = []
        for url in urls:
            if isinstance(url, str) and url.strip():
                cleaned_url = url.strip()
                # Basic URL validation
                if cleaned_url.startswith(('http://', 'https://')):
                    cleaned_urls.append(cleaned_url)
                else:
                    cleaned_urls.append(f'https://{cleaned_url}')
        
        if not cleaned_urls:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '沒有有效的網址'})
            }
        
        # Process URLs batch
        results = []
        sv_link_api_url = 'https://sv.link/api/v2/links'
        
        # Request headers for sv.link API
        sv_headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key.strip(),
            'User-Agent': 'StreetVoice-Batch-Generator/1.0'
        }
        
        for i, url in enumerate(cleaned_urls):
            try:
                # Prepare request payload for sv.link
                payload = {
                    'target': url,
                    'domain': 'sv.link'
                }
                
                # Make request to sv.link API
                response = requests.post(
                    sv_link_api_url,
                    headers=sv_headers,
                    json=payload,
                    timeout=15,  # 15 second timeout
                    allow_redirects=False
                )
                
                if response.status_code == 201:
                    # Success - parse response
                    try:
                        data = response.json()
                        short_url = data.get('shortUrl') or data.get('link') or data.get('id')
                        
                        if short_url:
                            # Ensure short URL has proper protocol
                            if not short_url.startswith('http'):
                                short_url = f"https://{short_url}"
                            
                            results.append({
                                'original': url,
                                'short': short_url,
                                'success': True
                            })
                        else:
                            results.append({
                                'original': url,
                                'short': 'API 回應格式錯誤',
                                'success': False
                            })
                    
                    except json.JSONDecodeError:
                        results.append({
                            'original': url,
                            'short': 'API 回應無法解析',
                            'success': False
                        })
                
                elif response.status_code == 400:
                    results.append({
                        'original': url,
                        'short': '網址格式錯誤',
                        'success': False
                    })
                
                elif response.status_code == 401:
                    results.append({
                        'original': url,
                        'short': 'API Key 無效',
                        'success': False
                    })
                
                elif response.status_code == 429:
                    results.append({
                        'original': url,
                        'short': 'API 請求頻率超限',
                        'success': False
                    })
                
                else:
                    results.append({
                        'original': url,
                        'short': f'HTTP {response.status_code} 錯誤',
                        'success': False
                    })
                
                # Small delay between requests to avoid rate limiting
                if i < len(cleaned_urls) - 1:  # Don't delay after last request
                    time.sleep(0.1)  # 100ms delay
                
            except requests.exceptions.Timeout:
                results.append({
                    'original': url,
                    'short': '請求超時',
                    'success': False
                })
            
            except requests.exceptions.ConnectionError:
                results.append({
                    'original': url,
                    'short': '連線失敗',
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
        
        # Prepare response summary
        total_count = len(results)
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'results': results,
                'summary': {
                    'total': total_count,
                    'success': success_count,
                    'failed': total_count - success_count
                },
                'message': f'批次處理完成：{success_count}/{total_count} 個網址成功生成短網址'
            }, ensure_ascii=False)
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': '請求內容 JSON 格式錯誤'})
        }
    
    except Exception as e:
        # Log error for debugging (in production, use proper logging)
        print(f"Unexpected error in shorten_url function: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': '伺服器內部錯誤',
                'details': str(e)[:100]  # Limit error message length
            })
        }