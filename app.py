from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

SALESLOFT_API_KEY = 'your_salesloft_api_key'

@app.route('/salesloft', methods=['POST'])
def salesloft_api():
    data = request.json
    response = requests.get(
        'https://api.salesloft.com/v2/people.json',
        headers={'Authorization': f'Bearer {SALESLOFT_API_KEY}'}
    )
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
