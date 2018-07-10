#-*- coding:utf-8 -*-
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import *
import pymongo


client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]


browser = webdriver.Chrome()
#browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)
# browser.set_window_size(1680,1050)
wait = WebDriverWait(browser, 20)


def search():
    browser.get('https://www.taobao.com')
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))
        )
        submit = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#J_TSearchForm > div.search-button > button"))
        )
        input.send_keys(KEY_WORD)
        submit.click()
        total = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))
        return total.text
    except TimeoutException:
        search()


def next_page(page_number):
    try:
        input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > input"))
        )
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit'))
                            )
        input.clear()
        input.send_keys(str(page_number))
        submit.click()
        wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active'), str(page_number)))
    except TimeoutException:
        next_page(page_number)


def parse_page_html():
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')))
        html = browser.page_source
        soup = BeautifulSoup(html, 'lxml')
        items = soup.select('#mainsrp-itemlist .items .item')
        print(u'此页共%d个商品' % len(items))
        for item in items:
            result = {
                'title': item.select('.title')[0].get_text().strip(),
                'img': item.select('.J_ItemPic')[0]['src'],
                'deal': item.select('.deal-cnt')[0].get_text()[:-3],
                'price': item.select('.price')[0].get_text().strip(),
                'location': item.select('.location')[0].get_text(),
            }
            save_to_mongo(result)
    except TimeoutException:
        parse_page_html()


def save_to_mongo(result):
    try:
        db[MONGO_TABLE].insert(result)
        print(u'保存成功', result)
    except Exception as e:
        print(u"保存失败", result)


def main():
    total = search()
    total = int(re.compile(r'(\d+)', re.S).search(total).group(1))
    print(u'共%d页' % total)
    try:
        print(u'正在爬取第1页')
        parse_page_html()
        for page_number in range(2, total + 1):
            print(u'正在爬取第%d页' % page_number)
            next_page(page_number)
            parse_page_html()
    except Exception as e:
        print(e, u'出错了...')
    finally:
        browser.close()


if __name__ == '__main__':
    main()
