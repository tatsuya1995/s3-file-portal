import boto3
import os
from datetime import datetime
from urllib.parse import quote, unquote

s3 = boto3.client('s3')

def handler(event, context):
    print('=== Lambda@Edge Debug Start ===')
    print('event:', event)
    request = event['Records'][0]['cf']['request']
    
    # Extract bucket name from the CloudFront domain name
    try:
        domain_name = request['origin']['s3']['domainName']
        print('domain_name:', domain_name)
        bucket_name = domain_name.split('.')[0]
        print('bucket_name:', bucket_name)
    except Exception as e:
        print('Error extracting bucket name:', e)
        raise
    
    # ダウンロードリクエストの場合
    if request['uri'] == '/download':
        # クエリパラメータからファイル名を取得
        query = request.get('querystring', '')
        file_key = None
        for param in query.split('&'):
            if param.startswith('file='):
                file_key = unquote(param[5:])
                break
        print('download file_key:', file_key)
        if file_key:
            # S3の該当ファイルへリダイレクト
            return {
                'status': '302',
                'statusDescription': 'Found',
                'headers': {
                    'location': [{
                        'key': 'Location',
                        'value': f'/{file_key}'
                    }]
                }
            }
        else:
            return {
                'status': '400',
                'statusDescription': 'Bad Request',
                'body': 'file parameter is required.'
            }

    # 通常のルートパス
    if request['uri'] == '/':
        try:
            response = s3.list_objects_v2(Bucket=bucket_name)
            print('S3 list_objects_v2 response:', response)
            files = response.get('Contents', [])
            print('files:', files)
            html_content = """
            <!DOCTYPE html>
            <html lang=\"ja\">
            <head>
                <meta charset=\"UTF-8\">
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                <title>S3 File Portal</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 2rem; background-color: #f4f7f9; color: #333; }
                    .container { max-width: 960px; margin: 0 auto; background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
                    h1, h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }
                    table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; }
                    th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #ecf0f1; }
                    tr:hover { background-color: #f9f9f9; }
                    a { color: #3498db; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    .download-btn { padding: 0.4rem 1rem; background-color: #27ae60; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 0.95rem; transition: background 0.2s; }
                    .download-btn:hover { background-color: #219150; }
                    .upload-form { margin-top: 2rem; padding: 1.5rem; border: 1px dashed #ccc; border-radius: 8px; background-color: #fafafa; }
                    .upload-form input[type=\"file\"] { display: block; margin-bottom: 1rem; }
                    .upload-form button { padding: 0.5rem 1rem; background-color: #3498db; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
                    .upload-form button:hover { background-color: #2980b9; }
                    #upload-status { margin-top: 1rem; font-weight: bold; }
                </style>
            </head>
            <body>
                <div class=\"container\">
                    <h1>S3 File Portal</h1>
            """
            html_content += """
                    <h2>File List</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>File Name</th>
                                <th>Size (Bytes)</th>
                                <th>Last Modified</th>
                                <th>Download</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            if files:
                for idx, file in enumerate(files):
                    file_key = file['Key']
                    size = file['Size']
                    last_modified = file['LastModified'].strftime("%Y-%m-%d %H:%M:%S")
                    html_content += f"""
                            <tr>
                                <td>{idx + 1}</td>
                                <td><a href=\"/{file_key}\">{file_key}</a></td>
                                <td>{size}</td>
                                <td>{last_modified}</td>
                                <td><a class=\"download-btn\" href=\"/download?file={quote(file_key)}\">ダウンロード</a></td>
                            </tr>
                    """
            else:
                html_content += '<tr><td colspan="5" style="text-align:center;">No files in bucket.</td></tr>'
            html_content += """
                        </tbody>
                    </table>
            """
            html_content += """
                    <div class=\"upload-form\">
                        <h2>Upload a file</h2>
                        <form id=\"upload-form\">
                            <input type=\"file\" id=\"file-input\" required />
                            <button type=\"submit\">Upload</button>
                        </form>
                        <p id=\"upload-status\"></p>
                    </div>
                </div>
                <script>
                    document.getElementById('upload-form').addEventListener('submit', async (event) => {
                        event.preventDefault();
                        const fileInput = document.getElementById('file-input');
                        const file = fileInput.files[0];
                        const statusElement = document.getElementById('upload-status');
                        if (!file) {
                            statusElement.textContent = 'Please select a file to upload.';
                            return;
                        }
                        statusElement.textContent = 'Getting upload URL...';
                        try {
                            const res = await fetch(`/upload-url?filename=${encodeURIComponent(file.name)}`);
                            if (!res.ok) throw new Error(`Failed to get upload URL: ${res.statusText}`);
                            const { url } = await res.json();
                            statusElement.textContent = 'Uploading...';
                            const uploadRes = await fetch(url, {
                                method: 'PUT',
                                body: file,
                                headers: { 'Content-Type': file.type }
                            });
                            if (uploadRes.ok) {
                                statusElement.textContent = "Upload successful! Page will reload shortly.";
                                setTimeout(() => location.reload(), 2000);
                            } else {
                                throw new Error(`Upload failed: ${uploadRes.statusText}`);
                            }
                        } catch (error) {
                            console.error('Error:', error);
                            statusElement.textContent = `An error occurred: ${error.message}`;
                            alert(`An error occurred: ${error.message}`);
                        }
                    });
                </script>
            </body>
            </html>
            """
            print('=== Lambda@Edge Debug End ===')
            return {
                'status': '200',
                'statusDescription': 'OK',
                'headers': {
                    'cache-control': [{'key': 'Cache-Control', 'value': 'max-age=0, no-cache, no-store, must-revalidate'}],
                    'content-type': [{'key': 'Content-Type', 'value': 'text/html'}]
                },
                'body': html_content
            }
        except Exception as e:
            print('Exception in S3 listing or HTML generation:', e)
            return {
                'status': '500',
                'statusDescription': 'Internal Server Error',
                'body': f'An error occurred while listing files. {e}'
            }
    return request 