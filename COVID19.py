from __future__ import unicode_literals
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models.send_messages import ImageSendMessage
import requests
import configparser
import re
import matplotlib.pyplot as plt
import pathlib
import pyimgur


app = Flask(__name__)

# LINE 聊天機器人的基本資料
config = configparser.ConfigParser()
config.read('config.ini')

# 用來串接Message-api的資料
line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))


# 接收 LINE 的資訊
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        print(body, signature)
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return 'OK'

# test, 回傳格式為json
r = requests.get('https://corona-api.com/countries')
data = r.json()
# 此陣列儲存在此API中所有country對應的ISO3166-1 code,之後查訊會用到
countrycode = []
for i in range(len(data["data"])):
    countrycode.append(
        {'name': data["data"][i]["name"], 'code': data["data"][i]["code"]})

# 查訊正確名稱,為了確保使用者的輸入正確, e.g.輸入korea,得到 Korea和Democratic People's Republic of、S. Korea
def rightcountryname(input):
    # 儲存多個country name
    templist=[]
    # 找找看有沒有重名的或是裡面有幾個字是對的
    for i in range(len(countrycode)):
        if input.lower() in countrycode[i]['name'].lower():
            templist.append(countrycode[i]['name'])   
    return '你輸入的關鍵字查詢結果：' + '、'.join(templist)


# 從指令中找國家名:今日即時資訊
def substringforcountryname(Allinput):
    # 關鍵字必須要包含,今日即時資訊, 否則回傳error
    if '今日即時資訊' in Allinput:
        # 找今日即時資訊最後一個字的index值
        for match in re.finditer('今日即時資訊', Allinput):
            print (match.start(), match.end())
            end = match.end()
            print(end)

        countryname = ''
        
        # 今日即時資訊後開始找國家名
        for i in range(end, len(Allinput)):
            if(Allinput[i] != ' '):
                countryname += Allinput[i]
        return countryname
    else:
        return 'keywords error'

# 轉換countryname to countryISO
def convertToISO(countryinput):
    for i in range(len(countrycode)):
        if countrycode[i]['name'].lower() == countryinput.lower():
            return countrycode[i]['code']
            break
    return 'notfound'

# 單一國家即時資料
def get_A_CountryRealTimeData(countryinput_only_realtime):
    req_only_now = requests.get('https://corona-api.com/countries')
    datanow = req_only_now.json()
    
    # 紀錄要用數值
    list = {}
    
    # 要輸出給LINEBOT的結果, default為未變
    result = ''
    
    # 紀錄是否有>1的國家
    country = []
    
    # 用來記錄輸入國家是否完全和api資料名稱相同
    match = False
    
    for i in range(len(datanow['data'])):
        # 這樣假設是為了讓使用者有更多彈性的使用空間, 不需打完全部的名字
        if countryinput_only_realtime.lower().replace(" ", "") in datanow['data'][i]['name'].lower().replace(" ", ""):
            print(datanow['data'][i])
            list['name'] = datanow['data'][i]['name']
            
            list['population'] = datanow['data'][i]['population']
            
            list['todaydeaths'] = datanow['data'][i]['today']['deaths']
            
            list['todayconfirmed'] = datanow['data'][i]['today']['confirmed']

            list['totaldeaths'] = datanow['data'][i]['latest_data']['deaths']

            list['totalrecovered'] = datanow['data'][i]['latest_data']['recovered']
            
            list['totalconfirmed'] = datanow['data'][i]['latest_data']['confirmed']

            list['death_rate'] = datanow['data'][i]['latest_data']['calculated']['death_rate']
            
            list['updated_at'] = datanow['data'][i]['updated_at']
                        
            # 紀錄查詢到的國家數量
            country.append(datanow['data'][i]['name'])
            
            # 用來處理若國家重名的情況, e.g. Sudan & South Sudan, 若查詢的為 Sudan 則應只回傳 Sudan的結果
            if(countryinput_only_realtime.lower().replace(" ", "") == datanow['data'][i]['name'].lower().replace(" ", "")):
                match = True
                break
        
    # 處理超過2個重複的結果，且輸入未有完全符合的情況
    if len(country) > 1 and match is not True:
        result = '你輸入的國家有超過兩個查詢結果：' + '、'.join(country)+"，請輸入更精確的關鍵字。"
    # 未搜尋到國家的狀況
    elif(len(country) == 0):
        result = '未查詢到資料，請檢查是否有輸入錯誤指令或關鍵字。'
    # 回傳結果
    else:
        for i in list:
            # 用來判斷從api中取得的資料
            outcome = list[i]
            
            # 讓數字每三位有一個逗號
            if(isinstance(outcome, int)):
                outcome = str("{:,}".format(outcome))
            # 若有浮點數只處理到第二位
            elif(isinstance(outcome, float)):
                outcome = str(round(outcome, 2))
            # 處理沒有資料的情況
            elif(outcome is None):
                outcome = 'N/A'

            # 加入資料
            if(i == 'name'):
                result += "國家: " + outcome + "\n"
            elif(i == 'population'):
                result += "人口數: " + outcome + "\n"        
            elif(i == 'todayconfirmed'):
                result += "今日確診人數: " + outcome + "\n"
            elif(i == 'todaydeaths'):
                result += "今日死亡人數: " + outcome + "\n"
            elif(i == 'totalconfirmed'):
                result += "總確診人數: " + outcome + "\n"
            elif(i == 'totalrecovered'):
                result += "總恢復人數: " + outcome + "\n"
            elif(i == 'totaldeaths'):
                result += "總死亡人數: " + outcome + "\n"
            elif(i == 'death_rate'):
                result += "致死率: " + outcome + "%\n"
            elif(i == 'updated_at'):
                result += "更新時間: " + outcome[0:10] + "\n"
    return result

# 用來取得指令裡的國家名: 趨勢圖
def substringforcountrynameImage(Allinput):
    #關鍵字必須要包含'趨勢圖',否則回傳error
    if '趨勢圖' in Allinput:
        # 找'趨勢圖'最後一個字的index值
        for match in re.finditer('趨勢圖', Allinput):
            #print (match.start(), match.end())
            end = match.end()
            #print(end)

        countryname = ''
        
        # 從'趨勢圖'後開始找國家名
        for i in range(end, len(Allinput)):
            if(Allinput[i] != ' '):
                countryname += Allinput[i]
        return countryname
    else:
        return 'keywords error'


# 做單一國家簡單的確診人數折線圖, 從現在時間起的30天內
def getPlot(countryISO):
    # 處理找不到輸入國家的情況
    if(countryISO == 'notfound'):
        return str('沒有相關結果，請檢查輸入國家或關鍵字是否有誤。')
    else:
        req = requests.get("https://corona-api.com/countries/"+countryISO)
        dataAcountryMonth = req.json()

        # 用來紀錄不同日期和資料(date, new_confirmed)
        A_country = {}
        # 紀錄最多30天
        count = 0
        # timeline是以最新的時間為第一個index值, 所以直接從0取到第30個
        for i in range(len(dataAcountryMonth['data']['timeline'])):
                A_country[dataAcountryMonth['data']['timeline'][i]['date']] = dataAcountryMonth['data']['timeline'][i]['new_confirmed']
                count+=1
                # 到第30個就退出
                if(count == 30):
                    break
        # only date data
        countrydatelist = list(A_country.keys())
        # 把開頭(e.g.2021-)去掉, 不然畫在圖上會太雜
        for i in range(len(countrydatelist)):
            countrydatelist[i] = countrydatelist[i].replace(str(dataAcountryMonth['data']['updated_at'])[0:5],"")
        # '-'換成'/', 單純是我個人喜好XD
        for i in range(len(countrydatelist)):
            countrydatelist[i] = countrydatelist[i].replace("-","/")
        # only confirmed data    
        countrydeathslist = list(A_country.values())
        
        # 將值反轉, 這樣才可以從比較小的日期開始畫趨勢圖
        countrydatelist.reverse()
        countrydeathslist.reverse()

        # 設定圖的size
        plt.figure(figsize=(15,10),dpi=100,linewidth = 2)
        # 畫折線圖
        plt.plot(countrydatelist,countrydeathslist,'s-',color = 'r')
        # title設定
        plt.title("COVID19 daily confirmed population", x=0.5, y=1.03, fontsize=40)

        # 設定x軸標題及粗體
        plt.xlabel("Date", fontweight = "bold", fontsize = 20)
        # 設定y軸標題及粗體
        plt.ylabel("DailyConfimed", fontweight = "bold", fontsize = 20)

        # 讓x軸的值都轉45度不然會很擠
        plt.xticks(fontsize=15, rotation=45)
        plt.yticks(fontsize=20)

        # 設定label
        plt.legend(labels=[countryISO], loc = 'best',  prop={'size': 20})

        # 預設會用來上船的檔名
        imgname = 'plotresult.png'
        
        # 存圖
        plt.savefig(imgname)

        # 記住存圖的路徑
        result = str(pathlib.Path(imgname).parent.resolve()) + '/' + imgname

        return result
    
# 上傳圖片到imgur上供LINEBOT讀取
def uploading(imgpath):
    CLIENT_ID = "4a8a642de3b62a4" #這個是我用來上傳imgur圖片庫的ID
    PATH = imgpath # 會從getPlot拿到imgur的path
    title = "Uploaded with PyImgur" # 用PyImgur上傳的, 不過使用者看不到(?)

    # 上傳圖片後取得imgur的url
    im = pyimgur.Imgur(CLIENT_ID)
    uploaded_image = im.upload_image(PATH, title=title)
    link = str(uploaded_image.link)
    
    return link


# 回覆message
@handler.add(MessageEvent, message=TextMessage)
def echo(event):
    if event.source.user_id != "Udeadbeefdeadbeefdeadbeefdeadbeef":

        # 使用說明書
        if("使用" in event.message.text):
            reply_arr = []
            reply_arr.append(TextSendMessage(
                "您好！\n這裡是COVID19的即時資料庫喵♫♪♬\n以下是簡易的指令說明："))
            reply_arr.append(TextSendMessage(
                "1.想要查詢單一國家的即時資料\n       今日即時資訊 國家名(英文大小寫都可以)\n範例: 今日即時資訊 Taiwan"))
            reply_arr.append(TextSendMessage(
                "2.想要查詢單一國家的30天內的確診趨勢圖\n       趨勢圖 國家名(英文大小寫都可以)\n範例: 趨勢圖 Taiwan"))
            reply_arr.append(TextSendMessage(
                "3.不確定要想要查詢的國家的正確名字嗎?\n       英文名字 國家名(英文大小寫都可以)\n範例: 英文名字 Korea"))
            line_bot_api.reply_message(event.reply_token, reply_arr)
        # 今日即時資訊回覆
        elif("今日即時資訊" in event.message.text):
            # 獲取單一國家即時資料
            result = get_A_CountryRealTimeData(substringforcountryname(event.message.text))

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result)
            )
        # 趨勢圖回覆
        elif("趨勢圖" in event.message.text):
            plotlink = uploading(getPlot(convertToISO(substringforcountrynameImage(event.message.text))))
            
            line_bot_api.reply_message(
                event.reply_token, ImageSendMessage(
                    original_content_url=plotlink,
                    preview_image_url=plotlink
                ))
        # 國家查詢
        elif("英文名字" in event.message.text):
            correctname = rightcountryname(event.message.text)
            
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=correctname)
            )
            


if __name__ == "__main__":
    app.run()
