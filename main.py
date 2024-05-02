from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    # Slackからのチャレンジリクエストをチェック
    if 'challenge' in data:
        return jsonify({
            "challenge": data['challenge']
        })
    # その他のイベント処理
    return "Event received", 200

if __name__ == '__main__':
    app.run(debug=True, port=3000)
