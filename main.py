from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    # Slackからのチャレンジリクエストをチェック
    if 'challenge' in data:
        return JSONResponse({"challenge": data['challenge']})
    # その他のイベント処理
    return {"message": "Event received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
