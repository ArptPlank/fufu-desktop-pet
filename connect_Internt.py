import re
import time
from bs4 import BeautifulSoup
import html2text
from playwright.sync_api import sync_playwright
import requests
import json
def search_keyword_and_collect_data(keyword):
    results = []  # List to store the results
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch(headless=False)  # Set headless=False to see the browser interaction
        page = browser.new_page()

        page.goto('https://www.baidu.com')
        page.fill('input[name="wd"]', keyword)
        page.click('input[id="su"]')

        # Wait for a specific timeout instead of waiting for a selector
        page.wait_for_timeout(3000)  # Wait for 5000 milliseconds (5 seconds)
        # Retrieve links from the search results
        links = page.query_selector_all('h3 a')
        urls = [link.get_attribute('href') for link in links]
        # Visit each link and extract data
        for index,url in enumerate(urls):
            try:
                page.goto(url)
                # Optional: Wait a bit for each page to load
                page.wait_for_timeout(2000)  # Wait for 3000 milliseconds (3 seconds)
                # Get the page title
                page_title = page.title()
                # Get all text from the body of the page
                body_text = page.text_content('body')  # Fetch all text from the body element
                html = page.content()
                h = html2text.HTML2Text()
                h.ignore_links = True
                markdown = h.handle(html)
                #print(markdown)
                # Extract only Chinese text
                #chinese_text = ''.join(re.findall(r'[\u4e00-\u9fff]+', body_text))
                # Store title and content in the results list
                results.append({"url": url, "title": page_title, "content": markdown})
                if index >= 3:
                    break
            except Exception as e:
                print(f"Failed to visit {url} with error: {e}")

        # Close the browser
        browser.close()
    data = ''
    for index, item in enumerate(results):
        data += f"{item['content']}\n"
    if len(data) > 2048:
        data = data[:2048]
    return data

def get_location():
    #response = requests.get('http://ipinfo.io/json')dddddddddddddddddddddddddddddddddddddddddddddd
    response = requests.get('http://myip.ipip.net')
    country = response.text.split('来自于：')[1].split(' ')[0]
    city = response.text.split('来自于：')[1].split(' ')[1]
    return f"当前位置：{country} {city}"

def get_weather(city):
    response = requests.get('https://weather.cma.cn/web/weather/58433.html')
    #设置编码
    response.encoding = 'utf-8'
    #解析网页
    soup = BeautifulSoup(response.text, 'html.parser')
    weather = []
    weather.append(soup.find('div', class_='pull-left day actived'))
    weather += soup.find_all('div', class_='pull-left day')
    for index, item in enumerate(weather):
        #print(item)
        weather_1 = [x.text.replace(',','').replace('\n','').replace(' ','').strip() for x in item.find_all('div', class_='day-item')]
        weather_1.pop(1)
        weather_1.pop(5)
        high_temperature = item.find('div', class_='high').text.replace(',','').replace('\n','').replace(' ','').strip()
        low_temperature = item.find('div', class_='low').text.replace(',','').replace('\n','').replace(' ','').strip()
        weather_1.append(high_temperature)
        weather_1.append(low_temperature)
        weather_1 = {"日期": weather_1[0],"白天":{"天气":weather_1[1],"风向":weather_1[2],"风力":weather_1[3],"最高温度":weather_1[4][:3],"最低温度":weather_1[4][3:]},"夜间":{"天气":weather_1[5],"风向":weather_1[6],"风力":weather_1[7],"温度":weather_1[8]}}
        weather[index] = weather_1
    #json格式化
    weather = json.dumps(weather, ensure_ascii=False)
    return weather


if __name__ == "__main__":
    # data = search_keyword_and_collect_data("枫丹")
    # print(data)
    location = get_location()
    get_weather(location[1])

# import re
# import time
# from playwright.sync_api import sync_playwright
# def search_keyword_and_collect_data(keyword):
#     results = []  # List to store the results
#     with sync_playwright() as p:
#         # Launch the browser
#         browser = p.chromium.launch(headless=False)  # Set headless=False to see the browser interaction
#         page = browser.new_page()
#
#         page.goto(f"https://www.bing.com/search?q={keyword}")
#
#         # Wait for a specific timeout instead of waiting for a selector
#         page.wait_for_timeout(3000)  # Wait for 5000 milliseconds (5 seconds)
#         # Retrieve links from the search results
#         h2 = page.query_selector_all('.b_algo')
#         h3 = [h2[i].query_selector('.b_tpcn') for i in range(len(h2))]
#         links = [h3[i].query_selector('a') for i in range(len(h3))]
#         urls = [link.get_attribute('href') for link in links]
#         # Visit each link and extract data
#         for index,url in enumerate(urls):
#             try:
#                 page.goto(url)
#                 # Optional: Wait a bit for each page to load
#                 page.wait_for_timeout(2000)  # Wait for 3000 milliseconds (3 seconds)
#                 # Get the page title
#                 page_title = page.title()
#                 # Get all text from the body of the page
#                 body_text = page.text_content('body')  # Fetch all text from the body element
#                 # Extract only Chinese text
#                 chinese_text = ''.join(re.findall(r'[\u4e00-\u9fff]+', body_text))
#                 # Store title and content in the results list
#                 results.append({"url": url, "title": page_title, "content": chinese_text})
#                 if index >= 3:
#                     break
#             except Exception as e:
#                 print(f"Failed to visit {url} with error: {e}")
#
#         # Close the browser
#         browser.close()
#     data = ''
#     temp = ''
#     for index, item in enumerate(results):
#         data += f"{item['content']}\n"
#     if len(data) > 1024:
#         data = data[:1024]
#     return data
#
# if __name__ == "__main__":
#     data = search_keyword_and_collect_data("枫丹")
#     print(data)

