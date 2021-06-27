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


# test
r = requests.get('https://corona-api.com/countries')
data = r.json()

# 查訊正確名稱,為了確保使用者的輸入正確
def rightcountryname(input):
    templist=[]
    for i in range(len(countrycode)):
        if input.lower() in countrycode[i]['name'].lower():
            templist.append(countrycode[i]['name'])

    
    return '你輸入的關鍵字查詢結果：' + '、'.join(templist)


# 此陣列儲存所有country對應的ISO3166-1 code,之後查訊會用到
countrycode = []
for i in range(len(data["data"])):
    countrycode.append(
        {'name': data["data"][i]["name"], 'code': data["data"][i]["code"]})

# 找關鍵國家字
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

# 轉換countryISO
def convertToISO(countryinput):
    for i in range(len(countrycode)):
        if countrycode[i]['name'].lower() == countryinput.lower():
            return countrycode[i]['code']
            break
    return 'notfound'

#單一國家即時資料
def get_A_CountryRealTimeData(countryinput_only_realtime):
    req_only_now = requests.get('https://corona-api.com/countries')
    datanow = req_only_now.json()
    
    # 紀錄要用數值
    list = {}
    
    # 要輸出給LINEBOT的結果, default為未變
    result = ''
    
    # 紀錄是否有>1的國家
    country = []
    
    match = False
    
    for i in range(len(datanow['data'])):
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
            
            print(list)
            
            # 紀錄查詢到的國家
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
        result = '未查詢到資料，請檢查是否有輸入錯誤指令或關鍵字'
    # 回傳結果
    else:
        for i in list:
            outcome = list[i]


            if(isinstance(outcome, int)):
                outcome = str("{:,}".format(outcome))
            elif(isinstance(outcome, float)):
                outcome = str(round(outcome, 2))
            elif(outcome is None):
                outcome = 'N/A'

            print(outcome)
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

# 用來取得畫圖關鍵字裡面的國家名
def substringforcountrynameImage(Allinput):
    #關鍵字必須要包含,畫圖, 否則回傳error
    if '畫圖' in Allinput:
        # 找畫圖關鍵字最後一個字的index值
        for match in re.finditer('畫圖', Allinput):
            #print (match.start(), match.end())
            end = match.end()
            #print(end)

        countryname = ''
        
        # 畫圖關鍵字後開始找國家名
        for i in range(end, len(Allinput)):
            if(Allinput[i] != ' '):
                countryname += Allinput[i]
        return countryname
    else:
        return 'keywords error'


# 做單一國家簡單的確診人數折線圖, 30天內
def getPlot(countryISO):
    if(countryISO == 'notfound'):
        return "沒有相關結果，請檢查輸入國家或關鍵字是否有誤"
    else:
        req = requests.get("https://corona-api.com/countries/"+countryISO)
        dataAcountryMonth = req.json()

        A_country = {}
        count = 0
        for i in range(len(dataAcountryMonth['data']['timeline'])):
                A_country[dataAcountryMonth['data']['timeline'][i]['date']] = dataAcountryMonth['data']['timeline'][i]['new_confirmed']
                count+=1
                if(count == 30):
                    break

        countrydatelist = list(A_country.keys())
        for i in range(len(countrydatelist)):
            countrydatelist[i] = countrydatelist[i].replace(str(dataAcountryMonth['data']['updated_at'])[0:5],"")
        for i in range(len(countrydatelist)):
            countrydatelist[i] = countrydatelist[i].replace("-","/")
        countrydeathslist = list(A_country.values())
        countrydatelist.reverse()
        countrydeathslist.reverse()

        plt.figure(figsize=(15,10),dpi=100,linewidth = 2)

        plt.plot(countrydatelist,countrydeathslist,'s-',color = 'r')

        plt.title("COVID19 daily confirmed population", x=0.5, y=1.03, fontsize=40)

        plt.xlabel("Date", fontweight = "bold", fontsize = 20)                # 設定x軸標題及粗體
        plt.ylabel("DailyConfimed", fontweight = "bold", fontsize = 20)    # 設定y軸標題及粗體

        plt.xticks(fontsize=15, rotation=45)
        plt.yticks(fontsize=20)

        plt.legend(labels=[countryISO], loc = 'best',  prop={'size': 20})

        
        imgname = 'plotresult.png'
        
        # 存圖
        plt.savefig(imgname)

        # 記住存圖的路徑
        result = str(pathlib.Path(imgname).parent.resolve()) + '/' + imgname
        #plt.show()

        # return Path
        return result
    
# 上傳圖片到imgur上供LINEBOT讀取
def uploading(imgpath):
    CLIENT_ID = "4a8a642de3b62a4" #這個是我用來上傳imgur圖片庫的ID
    PATH = imgpath #A Filepath to an image on your computer"
    title = "Uploaded with PyImgur"

    im = pyimgur.Imgur(CLIENT_ID)
    uploaded_image = im.upload_image(PATH, title=title)
    #print(uploaded_image.title)
    #print(uploaded_image.link)
    #print(uploaded_image.type)
    link = str(uploaded_image.link)
    
    return link

# 回覆message
@handler.add(MessageEvent, message=TextMessage)
def pretty_echo(event):

    if event.source.user_id != "Udeadbeefdeadbeefdeadbeefdeadbeef":


        if("使用" in event.message.text):
            reply_arr = []
            reply_arr.append(TextSendMessage(
                "您好！\n這裡是COVID19的即時資料庫喵♫♪♬\n以下是簡易的指令說明："))
            reply_arr.append(TextSendMessage(
                "1.想要查詢單一國家的即時資料\n       今日即時資訊 國家名(英文大小寫都可以)\n範例: 今日即時資訊 Taiwan"))
            line_bot_api.reply_message(event.reply_token, reply_arr)
        elif("今日即時資訊" in event.message.text):
            # 獲取單一國家即時資料
            result = get_A_CountryRealTimeData(substringforcountryname(event.message.text))

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result)
            )
        elif("畫圖" in event.message.text):
            plotlink = uploading(getPlot(convertToISO(substringforcountrynameImage(event.message.text))))
            

            line_bot_api.reply_message(
                event.reply_token, ImageSendMessage(
                    original_content_url=plotlink,
                    preview_image_url=plotlink
                ))
            




if __name__ == "__main__":
    app.run()
