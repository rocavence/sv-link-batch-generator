"""
StreetVoice sv.link 批次短網址生成器 - CSV 匯出 API
Netlify Function for exporting results to CSV format
"""

import json
import csv
import io
import base64
from datetime import datetime


def handler(event, context):
    """
    Netlify Function handler for CSV export
    """
    # CORS headers for cross-origin requests
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
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
        results = body.get('results', [])
        export_type = body.get('type', 'csv')
        
        # Validate input parameters
        if not results or not isinstance(results, list):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '缺少結果數據或格式錯誤'})
            }
        
        if len(results) == 0:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': '沒有可匯出的數據'})
            }
        
        # Validate export type
        if export_type not in ['csv']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f'不支援的匯出格式: {export_type}',
                    'supported_types': ['csv']
                })
            }
        
        # Generate CSV content
        if export_type == 'csv':
            csv_content = generate_csv(results)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'sv-link-results_{timestamp}.csv'
            
            # Encode content to base64 for safe transmission
            csv_base64 = base64.b64encode(csv_content.encode('utf-8-sig')).decode()
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'content': csv_base64,
                    'filename': filename,
                    'mimetype': 'text/csv;charset=utf-8;',
                    'size': len(csv_content),
                    'encoding': 'base64'
                }, ensure_ascii=False)
            }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': '請求內容 JSON 格式錯誤'})
        }
    
    except Exception as e:
        # Log error for debugging
        print(f"Unexpected error in export_data function: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': '伺服器內部錯誤',
                'details': str(e)[:100]
            })
        }


def generate_csv(results):
    """
    Generate CSV content from results data
    
    Args:
        results (list): List of URL processing results
        
    Returns:
        str: CSV content as string
    """
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Write CSV header
    header = [
        '序號',
        '原始網址',
        '短網址',
        '狀態',
        '處理時間'
    ]
    writer.writerow(header)
    
    # Generate timestamp for this export
    export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Write data rows
    for index, result in enumerate(results, 1):
        # Extract data with defaults
        original_url = result.get('original', '未知')
        short_url = result.get('short', '生成失敗')
        success = result.get('success', False)
        
        # Determine status
        status = '成功' if success else '失敗'
        
        # Write row
        row = [
            index,                  # 序號
            original_url,          # 原始網址
            short_url,             # 短網址
            status,                # 狀態
            export_time            # 處理時間
        ]
        
        writer.writerow(row)
    
    # Add summary row
    total_count = len(results)
    success_count = sum(1 for r in results if r.get('success', False))
    failed_count = total_count - success_count
    
    # Empty row separator
    writer.writerow([])
    
    # Summary section
    writer.writerow(['=== 處理摘要 ==='])
    writer.writerow(['總數量', total_count])
    writer.writerow(['成功數量', success_count])
    writer.writerow(['失敗數量', failed_count])
    writer.writerow(['成功率', f'{(success_count/total_count*100):.1f}%' if total_count > 0 else '0%'])
    writer.writerow(['匯出時間', export_time])
    writer.writerow(['工具', 'StreetVoice sv.link 批次短網址生成器'])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    return csv_content