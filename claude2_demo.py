from fastapi import FastAPI
import mimetypes
import uvicorn
import requests
import re
import uuid
import json

# 将获取的cookie和organization_uuid填到这里
cookie = ""
organization_uuid = ""


class Client:
    def __init__(self, conversation_uuid):
        self.cookie = cookie
        self.organization_uuid = organization_uuid
        self.conversation_uuid = conversation_uuid
        self.headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.79",
            "Referer": f"https://claude.ai/chat/{conversation_uuid}",
        }

    def chat_conversation(self, name):
        url = f'https://claude.ai/api/organizations/{self.organization_uuid}/chat_conversations'
        uuid4 = str(uuid.uuid4()) if self.conversation_uuid == "" else self.conversation_uuid
        payload = {
            "name": name,
            "uuid": uuid4
        }
        print(url, payload)
        response = requests.request('POST', url, json=payload, headers=self.headers)
        print(response.status_code)
        print(response.text)
        if response.status_code in [200, 201]:
            return uuid4
        else:
            return False

    # 发送消息到claude
    def append_message(self, prompt, attachments):
        url = "https://claude.ai/api/append_message"
        payload = {
            "completion": {
                "prompt": prompt,
                "timezone": "Asia/Shanghai",
                "model": "claude-2"
            },
            "organization_uuid": self.organization_uuid,
            "conversation_uuid": self.conversation_uuid,
            "text": prompt,
            "attachments": attachments
        }

        response = requests.request("POST", url, json=payload, headers=self.headers)
        response.encoding = 'utf-8'
        if response.status_code in [200, 201]:
            pattern = re.compile(r'data: (.*?)"type":"within_limit"}}', re.DOTALL)
            match = re.findall(pattern, response.text)
            if len(match) > 0:
                text = match[-1] + '"type":"within_limit"}}'
                text = json.loads(text.strip())["completion"]
                # print(text)
                print("发送消息成功", text)
                return text
        else:
            return False

    def convert_document(self, file_path):
        print("开始解析文件")
        url = 'https://claude.ai/api/convert_document'
        mimetype, encoding = mimetypes.guess_type(file_path)
        print(mimetype)
        # example pdf mimetype 'application/pdf'
        if mimetype is not None:
            files = [('file', (file_path, open(file_path, 'rb'), mimetype))]
            data = {"orgUuid": self.organization_uuid}
            headers = {
                "Cookie": self.headers['Cookie'],
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.headers['Referer']
            }
            response = requests.post(url, files=files, data=data, headers=headers)
            if response.status_code in [200, 201]:
                print("文件解析成功")
                data = response.json()
                return data
            else:
                print("文件解析失败")
                return False

        else:
            print("文件解析失败")
            return False


app = FastAPI()


@app.get('/claude/chat_conversation')
def createChatConversation(conversation_uuid: str = '', name: str = ''):
    client = Client(conversation_uuid)
    result = client.chat_conversation(name)
    if not result:
        return {
            "ok": "fail",
            "msg": "创建对话失败"
        }
    return {
        "ok": "success",
        "data": result
    }


@app.get('/claude/append_message')
def appendMessage(conversation_uuid: str, prompt: str, file: str = ''):
    client = Client(conversation_uuid)
    attachments = []
    if file != '':
        convert_result = client.convert_document(file)
        if not convert_result:
            return {
                "ok": "fail",
                "msg": "解析文件失败"
            }
        attachments.append(convert_result)
    r = client.append_message(prompt, attachments)
    if not r:
        return {
            "ok": "fail",
            "msg": "发送消息失败"
        }
    print("r--", r)
    return {
        "ok": "success",
        "data": r
    }


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
