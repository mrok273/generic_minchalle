from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
import os
import pytz
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
japan_timezone = pytz.timezone('Asia/Tokyo')
# Slackアプリの設定を初期化
app = App(
    token=SLACK_BOT_TOKEN,  # Bot User OAuth Token
    signing_secret=SLACK_SIGNING_SECRET  # アプリの設定ページから取得
)

# FastAPI用のハンドラーを作成
handler = SlackRequestHandler(app)



from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Boolean,Date
import requests
import re, os
from datetime import datetime
from dotenv import dotenv_values

app = FastAPI()

# PostgreSQL接続設定
# DATABASE_URL = os.environ.get("DATABASE_URL")
# print(DATABASE_URL)
# engine = create_engine(DATABASE_URL, echo=True)
# config = dotenv_values("./.env")
username = os.environ.get("DATABASE_USERNAME")
password = os.environ.get("DATABASE_PASSWORD")
dbname = os.environ.get("DATABASE_NAME")
port = os.environ.get("DATABASE_PORT",6543)
host = os.environ.get("DATABASE_HOST")
engine = create_engine(f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}", echo=True)

metadata = MetaData()

# テーブル定義 (この部分はすでにあると仮定)
teams = Table('team_progress', metadata,
    Column('id', Integer, primary_key=True),
    Column('date', Date),
    Column('team_name', String),
    Column('team_thread_ts', String),
    Column('user_id', String),
    Column('is_finished', Boolean)
    )

class SlackEvent(BaseModel): #使っていない？
    type: str
    channel: str
    user: str
    text: str
    ts: str


def find_slack_ids(text):
    #slackのuser_id
    pattern = r"<@([A-Z0-9]+)>"
    ids = re.findall(pattern, text)
    return ids

def insert_activity(event):
    # print(event)
    team_name = event["text"].split("\n")[1].split(" ")[0]
    team_thread_ts = event["ts"]
    user_id_list = find_slack_ids(event["text"])

    conn = engine.connect()
    data_to_insert = []
    for user_id in user_id_list:
        
        today = datetime.now(japan_timezone).strftime("%Y-%m-%d")
        info = {"date":today,
        "team_name":team_name,
        "team_thread_ts":team_thread_ts,
        "user_id":user_id,
        "is_finished":False}

        data_to_insert.append(info)
    
    # 複数行のデータを一度に挿入
    conn.execute(teams.insert(), data_to_insert)
    # 接続を閉じる
    conn.commit()
    conn.close()

def update_user_status(data):
    user_id = data["event"]["user"]
    team_thread_ts = data["event"]["thread_ts"]
    from sqlalchemy.sql import text as sql_text
    conn = engine.connect()
    query = sql_text(f"""
UPDATE team_progress SET is_finished = True WHERE team_thread_ts = '{team_thread_ts}' and user_id = '{user_id}'
""")
    conn.execute(query)

    #今何人中何人がtrueなのか数える
    query = sql_text(f"""
SELECT 
team_name
,COUNT(distinct case when is_finished = True then user_id else null end) as finished_user_count
,COUNT(distinct user_id) as total_user_count
FROM team_progress 
WHERE team_thread_ts = '{team_thread_ts}'
group by 1
""")
    result = conn.execute(query)
    row = result.fetchone()

    team_name = row[0]
    finished_user_count = row[1]#['finished_user_count']
    total_user_count = row[2]#['total_user_count']

    # メッセージの生成
    message = f"チーム{team_name}:{total_user_count}人中{finished_user_count}人が目標達成しました!!!"

    conn.commit()
    conn.close()

    send_message_to_slack(team_thread_ts, message, ":thumbsup:")


def send_message_to_slack(team_thread_ts, message,icon_emoji):
    url = 'https://slack.com/api/chat.postMessage'
    headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
    payload = {
        'channel': "C071E4WF48N",
        'text': message,
        'thread_ts': team_thread_ts,  # このメッセージをスレッドに投稿
        'as_user': True,
        'icon_url': icon_emoji, #うごかない・・・
        'username':"AAA"  #うごかない・・・
    }

    response = requests.post(url, headers=headers, json=payload)
    # return response.json()  # Slack APIからの応答をJSON形式で返す

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    # Slackからのチャレンジリクエストをチェック
    if 'challenge' in data:
        return JSONResponse({"challenge": data['challenge']})
    
    event_type = data["event"]["type"]
    if event_type == 'message':
        text = data['event']['text']

        if '===ahsiagkuutriamtaodrouka===' in text:
            # 上の文字列がある場合はスレッド作成された証
            insert_activity(data["event"])


    elif event_type == 'app_mention':
        if "U071LLBK90B" in data["event"]["text"]: #ジェネリックみんチャレ　にリプライ
            update_user_status(data)

    # その他のイベント処理
    return {"message": "Event received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
