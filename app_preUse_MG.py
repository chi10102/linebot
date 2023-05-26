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


#根據訊息內容  做處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    
    if event.message.text == '有哪些狗':
        line_bot_api.reply_message(
            event.reply_token,
            carousel_template1
        )

        # with open('about_01.json',encoding='utf-8') as d:     ### 暫定all dogs.json##################
        #     test = json.load(d)
        # line_bot_api.reply_message(
        # event.reply_token,FlexSendMessage('hello',test)
        # )
        

    elif event.message.text == '關於中原動服社':
        with open('about_01.json',encoding='utf-8') as d:
            test = json.load(d)
        line_bot_api.reply_message(
        event.reply_token,FlexSendMessage('hello',test)
        )  

    # elif event.message.text == '關於中原動服社':    
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         carousel_template2
    #     )     

    elif event.message.text == '猜猜什麼狗':
        # message = TemplateSendMessage(
        #     alt_text='Buttons template',
        #     template=ButtonsTemplate(
        #         thumbnail_image_url='https://imgur.com/FtPiVGL.jpg',#可改
        #         # imageBackgroundColor = "#deffe5",
        #         title='選擇一個動作',
        #         text='操作說明：使用者可透過相機拍照或從相簿選取照片，傳送至系統進行辨識。',
        #         actions=[
        #             URITemplateAction(
        #                 label='開啟相機',
        #                 uri='line://nv/camera/'
        #             ),
        #             URITemplateAction(
        #                 label='選取相片',
        #                 uri='line://nv/cameraRoll/single'
        #             )
        #         ]
        #     )
        # )
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


#--移動圖test (Carousel template message)      ##########所有狗狗介紹#####################
carousel_template1 = TemplateSendMessage(
    alt_text='Carousel Template 1',
    template=CarouselTemplate(
        columns=[
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/Yx8WJFz.jpg',
                title='1-我叫小黑',
                text='特徵：全黑，胖呼呼',              
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：食量大，喜歡挖洞和被拍屁屁\
                                個性：傲嬌屬性，其傲的屬性>嬌\
                                注意事項：不親狗"
                    }
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/gKNThaq.jpg',
                title='2-我叫小熊',
                text='特徵：尾巴短短',
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：會發出聲音的玩具\
                                個性：活潑直率，愛玩耍，相當親人\
                                注意事項：看見其他狗狗會太激動，想撲上去，會護食，怕孤單\
                                "
                    }
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/h0Q2OJd.jpg',
                title='3-我叫小斑',
                text='特徵：毛很柔順，走路像螃蟹歪歪的',
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：愛睡覺、喜歡純肉的零食\
                                個性：隨和友善，喜歡撒嬌\
                                注意事項：不親狗、不喜歡各種快速移動的東西、不喜歡長者\
                                "
                    }
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/GAEWDKy.jpg',
                title='4-我叫Q比',
                text='特徵：耳朵一豎一垂',
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：喜歡啃樹皮，挖洞和愛玩躲貓貓給人家找，還有喜歡淋雨的感覺\
                                個性：神出鬼沒，很有個性的小夥子\
                                注意事項：年紀很大，會護食\
                                "
                    }
                ]
            ),
            CarouselColumn( 
                thumbnail_image_url='https://imgur.com/plSR5h0.jpg',
                title='5-我叫莎白',
                text='特徵：白襪子，胸前嘴邊有白毛',
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：貪吃、愛搗蛋、挖土\
                                個性：調皮，很多奇葩的舉動\
                                注意事項：不親狗、怕球、會亂吃東西、不喜歡高大的男性\
                                "
                    }
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/G2CDzLE.jpg',
                title='6-我叫土豆',
                text='特徵：柴犬尾巴',
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：貪吃、喜歡滾草地、握手王\
                                個性：喜歡討摸，握手王\
                                注意事項：不親狗、不喜歡各種快速移動的東西、不喜歡長者\
                                "
                    }
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://i.imgur.com/vPykFAz.jpg',
                title='7-我叫樂樂',
                text='特徵：肉嘟嘟，臉軟得像麻糬，尾巴很短',
                actions=[
                    {
                        "type": "message",
                        "label": "點我看介紹",
                        "text": "習性喜好：貪吃，食量大，狗舍唯一會玩球的毛小孩\
                                個性：害羞怕生，但熟了就會很真心對你微笑，跟你親近\
                                注意事項：有人群恐懼症和嚴重怕生，所以一開始接近他要慢慢試水溫建立信任，不然會嚇到牠呦\
                                "
                    }
                ]
            ),

        ]
    )
)
   

                                              ##########關於我們(FB/IG/蝦皮...)##################      
carousel_template2 = TemplateSendMessage(
    alt_text='Carousel Template 2',
    template=CarouselTemplate(
        columns=[
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/Z3R97BG.jpg',
                title='Facebook',
                text='一群愛動物、想為流浪動物盡一份心力的大學生們所組成的社團。',              
                actions=[
                    URIAction(label='前往動服社的FB', uri='https://www.facebook.com/cycucatdog/?locale=zh_TW'),
                    URIAction(label='連結2', uri='https://linkfly.to/30906q4vJGW')
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/V2hhTIw.jpg',
                title='Instagram',
                text='社團狗狗日常分享、社團及志工活動訊息。可愛的社團狗狗開放認養中，若發現需要幫助的動物請盡速與我們聯絡。',
                actions=[
                    URIAction(label='前往動服社的IG', uri='https://www.instagram.com/cycucatdog'),
                    URIAction(label='連結2', uri='https://linkfly.to/30906q4vJGW')
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/SCVGhYa.jpg',
                title='最新活動',
                text='歡迎社員們踴躍參加，到前線為動保議題付出，和我們一起在校內照顧狗狗，非社員也隨時歡迎入社～快行動起來吧！',
                actions=[
                    URIAction(label='最新活動公告', uri='https://www.instagram.com/p/CrsI9bsLjaM'),
                    URIAction(label='活動表單', uri='https://linkfly.to/30906q4vJGW')                 
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/fWUI7WQ.jpg',
                title='蝦皮賣場',
                text='本義賣商品之所得將全額分配至中原大學內每隻浪浪的食、藥支出，謝謝您們的愛心。',
                actions=[
                    URIAction(label='前往義賣區', uri='https://shopee.tw/enily871127'),
                    URIAction(label='連結2', uri='https://linkfly.to/30906q4vJGW')
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/bd8QZkd.jpg',
                title='PCT好侶',
                text='PCT好侶與學生社團長期合作，希望能將盡一份心力，減輕學生們的負擔，讓他們能有更多的時間幫助毛孩子們。',
                actions=[
                    URIAction(label='前往PCT好侶', uri='https://www.perfectcompanion.com.tw/tw/news/charity/67'),
                    URIAction(label='連結2', uri='https://linkfly.to/30906q4vJGW')
                ]
            ),
            CarouselColumn(
                thumbnail_image_url='https://imgur.com/9CbPvBl.jpg',
                title='社團法人台灣之心愛護動物協會',
                text='您也想要帶流浪貓狗去結紮嗎？請來電協會申請，即可完成紮浪浪計畫的申請手續、馬上使用本計畫的補助名額喔！',
                actions=[
                    URIAction(label='前往台灣之心愛護動物協會', uri='https://hotac.org.tw/content-tnr_projectJoin'),
                    URIAction(label='連結2', uri='https://linkfly.to/30906q4vJGW')
                ]
            )
        ]
    )
)



if __name__ == "__main__":
    app.run()
