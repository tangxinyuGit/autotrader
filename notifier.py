import requests
import datetime

def send_pushplus(token, title, content):
    """
    Sends notification via PushPlus.
    """
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": token,
        "title": title,
        "content": content
    }
    try:
        # In sandbox, we don't have a real token, so we just print.
        # response = requests.post(url, json=data)
        # return response.json()
        print(f"[{datetime.datetime.now()}] MOCK PushPlus Sent: {title} - {content}")
        return {"code": 200, "msg": "Mock Success"}
    except Exception as e:
        print(f"PushPlus Error: {e}")
        return None

def send_email(subject, body):
    # Mock email sender
    print(f"[{datetime.datetime.now()}] MOCK Email Sent: {subject} - {body}")

def notify(title, message):
    # You can configure your token here or load from env
    TOKEN = "YOUR_PUSHPLUS_TOKEN"

    # Print to console (always)
    print(f"--- NOTIFICATION: {title} ---\n{message}\n-----------------------------")

    # Send via channels
    send_pushplus(TOKEN, title, message)
    # send_email(title, message)
