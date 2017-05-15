# coding=utf-8
# To install the Python client library:
# pip install -U selenium

# Import the Selenium 2 namespace (aka "webdriver")
# import keyring
# from selenium.common.exceptions import ElementNotVisibleException
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
import os
import glob
import time
import urllib2
import cPickle
import json

OUTPUT_DIR = '/Users/msei/Downloads/flat_search_temp/'


def textIf(a):
    if len(a) >= 1:
        return a[0].text
    else:
        return ""


driver = webdriver.Firefox()  # (firefox_profile=profile)


def immobilienscout_list(driver):
    for i in range(2, 67):
        driver.get('https://www.immobilienscout24.de/Suche/S-T/P-' + str(
            i) + '/Wohnung-Miete/Bayern/Muenchen?pagerReporting=true')

        elements = list()

        results = driver.find_elements_by_class_name('result-list__listing')
        for result in results:
            for link in result.find_elements_by_class_name('result-list-entry__brand-title-container'):
                elements.append(link.get_attribute('href'))

        for page in elements:
            driver.get(page)

            id = page[str(page).rindex('/') + 1:-1]

            data = dict()
            tags = ""
            for info in driver.find_elements_by_class_name('boolean-listing'):
                for tag in info.find_elements_by_tag_name('span'):
                    tags += tag.text + ", "

            data['tags'] = tags
            data['title'] = textIf(driver.find_elements_by_id('expose-title'))
            data['address'] = textIf(driver.find_elements_by_class_name('address-block'))
            data['kaltmiete'] = textIf(driver.find_elements_by_class_name('is24qa-kaltmiete'))
            data['bezugsfrei'] = textIf(driver.find_elements_by_class_name('is24qa-bezugsfrei-ab'))
            data['kaution'] = textIf(driver.find_elements_by_class_name('is24qa-kaution-o-genossenschaftsanteile'))
            data['zimmer'] = textIf(driver.find_elements_by_class_name('is24qa-zimmer'))
            data['flaeche'] = textIf(driver.find_elements_by_class_name('is24qa-flaeche'))
            data['zimmer'] = textIf(driver.find_elements_by_class_name('is24qa-zi'))
            data['link'] = page

            with open(OUTPUT_DIR + '/immo24/' + str(id) +'.json', 'w') as fp:
                json.dump(data, fp)

            print data


immobilienscout_list(driver)
