"""
Vercel Function for CSV export
"""

import json
import csv
import io
import base64
from datetime import datetime


def handler(request):
    """Main handler function for CSV export"""
    
    # Handle CORS
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
            body = request.data if hasattr(request, 'data') else request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)
        
        results = data.get('results', [])
        
        if not results:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '沒有可匯出的數據'})
            }
        
        # Generate CSV content
        csv_content = generate_csv(results)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sv-link-results_{timestamp}.csv'
        
        # Encode content to base64
        csv_base64 = base64.b64encode(csv_content.encode('utf-8-sig')).decode()
        
        response_body = {
            'content': csv_base64,
            'filename': filename,
            'mimetype': 'text/csv;charset=utf-8;',
            'size': len(csv_content),
            'encoding': 'base64'
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
            'body': json.dumps({'error': f'匯出失敗: {str(e)}'})
        }


def generate_csv(results):
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