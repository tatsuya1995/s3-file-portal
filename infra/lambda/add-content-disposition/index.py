def handler(event, context):
    print('=== AddContentDisposition Lambda@Edge ORIGIN_RESPONSE ===')
    print('event:', event)
    response = event['Records'][0]['cf']['response']
    request = event['Records'][0]['cf']['request']
    uri = request.get('uri', '')
    query = request.get('querystring', '')
    print('uri:', uri)
    print('query:', query)
    print('response before:', response)

    # /download?file=... のときだけContent-Disposition: attachmentを付与
    try:
        if uri == '/download' and 'file=' in query:
            if 'headers' not in response or response['headers'] is None:
                response['headers'] = {}
            # 既存のcontent-dispositionがあれば上書き
            response['headers']['content-disposition'] = [{
                'key': 'Content-Disposition',
                'value': 'attachment'
            }]
            print('Content-Disposition header added!')
    except Exception as e:
        print('Exception in AddContentDisposition Lambda:', e)
    print('response after:', response)
    print('=== END ===')
    return response 