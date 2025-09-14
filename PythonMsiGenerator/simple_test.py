from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>Simple Test</title></head>
    <body>
        <h1>Flask Server is Working!</h1>
        <p>If you see this, the Flask server is running correctly.</p>
        <p>Server info:</p>
        <ul>
            <li>Port: 6000</li>
            <li>Host: 0.0.0.0</li>
            <li>Debug: True</li>
        </ul>
    </body>
    </html>
    '''

@app.route('/test')
def test():
    return {'status': 'working', 'message': 'API endpoint works'}

if __name__ == '__main__':
    print("Starting simple Flask test server...")
    print("Open: http://localhost:6000")
    app.run(debug=True, host='0.0.0.0', port=6000)