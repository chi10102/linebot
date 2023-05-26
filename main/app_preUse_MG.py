import os
import json
import numpy as np
import requests

# from PIL import Image, ImageOps
from flask import Flask, request, abort
import subprocess
import shutil



from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ButtonsTemplate, URITemplateAction, CarouselTemplate, CarouselColumn, URIAction, FlexSendMessage, CameraAction, CameraRollAction, QuickReply,
    QuickReplyButton, PostbackAction)
from linebot.exceptions import LineBotApiError

# ==========================================================================================
app = Flask(__name__, static_url_path='/static')        
UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])

config = configparser.ConfigParser()
config.read('config.ini')

line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))
my_line_id = config.get('line-bot', 'my_line_id')
end_point = config.get('line-bot', 'end_point')
line_login_id = config.get('line-bot', 'line_login_id')
line_login_secret = config.get('line-bot', 'line_login_secret')
my_phone = config.get('line-bot', 'my_phone')
HEADER = {
    'Content-type': 'application/json',
    'Authorization': F'Bearer {config.get("line-bot", "channel_access_token")}'
}

# ==========================================================================================

#我把資料都寫在env.json裡 記得進去裡面修改成自己要套用的Linebot API
with open('env.json') as f:
    env = json.load(f)
    
line_bot_api = LineBotApi(env['YOUR_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(env['YOUR_CHANNEL_SECRET'])
#---------imgur-----------
client_id = env['YOUR_IMGUR_ID']
access_token = env['IMGUR_TOKEN']
headers = {'Authorization': f'Bearer {access_token}'}



app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        print("Error occurred while handling webhook: ", e)
        abort(500)

    return 'OK'

# ==========================================================================================

@app.route("/", methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return 'ok'
    body = request.json
    events = body["events"]
    if request.method == 'POST' and len(events) == 0:
        return 'ok'
    print(body)
    if "replyToken" in events[0]:
        payload = dict()
        replyToken = events[0]["replyToken"]
        payload["replyToken"] = replyToken
        if events[0]["type"] == "message":
            if events[0]["message"]["type"] == "text":
                text = events[0]["message"]["text"]

                if text == "我的名字":
                    payload["messages"] = [getNameEmojiMessage()]
                elif text == "出去玩囉":
                    payload["messages"] = [getPlayStickerMessage()]
                elif text == "台北101":                                 ### 台北101圖片 ###
                    payload["messages"] = [getTaipei101ImageMessage(),
                                           getTaipei101LocationMessage(),
                                           getMRTVideoMessage()]
                elif text == "quoda":
                    payload["messages"] = [
                            {
                                "type": "text",
                                "text": getTotalSentMessageCount()
                            }
                        ]   
                elif text == "今日確診人數":
                    payload["messages"] = [
                            {
                                "type": "text",
                                "text": getTodayCovid19Message()
                            }
                        ]
                elif text == "主選單":
                    payload["messages"] = [
                            {
                                "type": "template",
                                "altText": "This is a buttons template",
                                "template": {
                                  "type": "buttons",
                                  "title": "Menu",
                                  "text": "Please select",
                                  "actions": [
                                      {
                                        "type": "message",
                                        "label": "我的名字",
                                        "text": "我的名字"
                                      },
                                      {
                                        "type": "message",
                                        "label": "今日確診人數",
                                        "text": "今日確診人數"
                                      },
                                      {
                                        "type": "uri",
                                        "label": "聯絡我",
                                        "uri": f"tel:{my_phone}"
                                      }
                                  ]
                              }
                            }
                        ]
                else:
                    payload["messages"] = [
                            {
                                "type": "text",
                                "text": text
                            }
                        ]
                replyMessage(payload)
            elif events[0]["message"]["type"] == "location":
                title = events[0]["message"]["title"]
                latitude = events[0]["message"]["latitude"]
                longitude = events[0]["message"]["longitude"]
                payload["messages"] = [getLocationConfirmMessage(title, latitude, longitude)]
                replyMessage(payload)
        elif events[0]["type"] == "postback":
            if "params" in events[0]["postback"]:
                reservedTime = events[0]["postback"]["params"]["datetime"].replace("T", " ")
                payload["messages"] = [
                        {
                            "type": "text",
                            "text": F"已完成預約於{reservedTime}的叫車服務"
                        }
                    ]
                replyMessage(payload)
            else:
                data = json.loads(events[0]["postback"]["data"])
                action = data["action"]
                if action == "get_near":
                    data["action"] = "get_detail"
                    payload["messages"] = [getCarouselMessage(data)]
                elif action == "get_detail":
                    del data["action"]
                    payload["messages"] = [getTaipei101ImageMessage(),
                                           getTaipei101LocationMessage(),
                                           getMRTVideoMessage(),
                                           getCallCarMessage(data)]
                replyMessage(payload)

    return 'OK'

# ==========================================================================================

#根據訊息內容  做處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    
    if event.message.text == '所有狗狗介紹':
        with open('all_dogs_0525.json',encoding='utf-8') as d:     ##### all_dogs_02.json###########
            test = json.load(d)
        line_bot_api.reply_message(
        event.reply_token,FlexSendMessage('有哪些狗',test)
        )        

    elif event.message.text == '關於中原動服社':
        with open('about_01.json',encoding='utf-8') as d:       ##### about_01.json##################
            test = json.load(d)
        line_bot_api.reply_message(
        event.reply_token,FlexSendMessage('中原動服社',test)
        )  

    # if event.message.text == '所有狗狗介紹':
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         carousel_template1
    #     )

    # elif event.message.text == '關於中原動服社':    
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         carousel_template2
    #     )     

    # elif event.message.text == '這隻狗叫什麼名字':
    #     message = TemplateSendMessage(
    #         alt_text='Buttons template',
    #         template=ButtonsTemplate(
    #             thumbnail_image_url='https://imgur.com/FtPiVGL.jpg',#可改
    #             # imageBackgroundColor = "#deffe5",
    #             title='選擇一個動作',
    #             text='操作說明：使用者可透過相機拍照或從相簿選取照片，傳送至系統進行辨識。',
    #             actions=[
    #                 URITemplateAction(
    #                     label='開啟相機',
    #                     uri='line://nv/camera/'
    #                 ),
    #                 URITemplateAction(
    #                     label='選取相片',
    #                     uri='line://nv/cameraRoll/single'
    #                 )
    #             ]
    #         )
    #     )
    elif event.message.text == '這隻狗叫什麼名字':    
        message=TextSendMessage(
            text="操作說明：\
                                                請從下面按鈕選擇開啟相機拍照或從相簿選取照片，傳送至系統進行辨識",
            quick_reply=QuickReply(
                items=[                    
                    QuickReplyButton(
                        action=CameraAction(label="拍照")
                        ),
                    QuickReplyButton(
                        action=CameraRollAction(label="相簿")
                        )
                        
                ]
            )
        )
        try:
            line_bot_api.reply_message(event.reply_token, message)
        except LineBotApiError as e:
            print('發生 LineBotApiError: ', e)


#大概運作流程=>
#-> 當bot接收到圖片
#-> 保存圖檔temp.jpg 
#-> 將圖片帶入執行detect.py 並產出標出名稱的圖檔 和txt檔(我加在detect裡) 然後放在LineExport資料夾裡
#-> 刪除temp.jpg 並把產出有標框線的圖上傳至imgur
#-> 讀取txt檔的結果 回傳給使用者
#-> 把LineExport資料夾刪除

#-----當使用者傳圖片時-----
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    with open('temp.jpg', 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)
            
    user_id = event.source.user_id

    line_bot_api.push_message(user_id, TextSendMessage(text='辨識進行中...請稍後'))
    if os.path.exists('LineExport'):
        shutil.rmtree('LineExport')
    # 帶入參數 執行 detect    
    result = subprocess.run(['python', 'detect.py', '--weights', 'best300.pt', '--conf-thres', '0.5', '--img-size', '416', '--source', 'temp.jpg', '--project', './', '--name', 'LineExport'],text=True)
    #os.remove('temp.jpg')

    print("==========================")
    print(result)#自己看爽用
    print("==========================")
    
    #狗勾標籤對應中文名稱
    Dog_CH = {
        'Black':'小黑',
        'Bear':'小熊',
        'Ben':'小斑',
        'Qbi':'Q比',
        'Sabai':'莎白',
        'Tudo':'土豆',
        'Lele':'樂樂'
    }
    

    imgur_link = upload_image_to_imgur('./LineExport/temp.jpg')
    
    #讀取標籤內容    
    with open("./LineExport/result.txt", "r") as f:
        content = f.read()
         
        if content:  # 有檢測結果
            Dogresult = (content.split(' '))[1].strip(',')
            dog_name = Dog_CH.get(Dogresult, "查無此狗")
                
            # 回傳圖片和結果給使用者
            if imgur_link:
                image_message = ImageSendMessage(original_content_url=imgur_link, preview_image_url=imgur_link)
                line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text=f'偵測完畢　他是{dog_name}:D'),
                    image_message
                ]
            )
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='上傳圖片到 Imgur 失敗'))
                    

            
                #刪除殘留檔 可刪可不刪
                #os.remove('result.txt')
                #shutil.rmtree('LineExport')
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='沒有偵測到狗狗，請重新上傳正確圖片'))
            
    # shutil.rmtree('LineExport')



# 傳圖片上imgur
def upload_image_to_imgur(image_path):
    url = 'https://api.imgur.com/3/upload'
    with open(image_path, 'rb') as f:
        response = requests.post(url, headers=headers, files={'image': f})
        if response.status_code == 200:
            return response.json().get('data').get('link')
        else:
            return None
#--------------------------------------------------------------------------------------







if __name__ == "__main__":
    app.run()
