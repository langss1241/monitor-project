from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import shutil
from platfrom_config import get_platfrom_config


COOKIES_DIR = "C:/Users/wsmian/Desktop/用户资金-流失/用户资金-流失/session"


def login_and_save_profile(platfrom_name):
    """登录指定平台并保存cookies"""
    config = get_platfrom_config(platfrom_name)
    if not config:
        print(f"❌ 未找到平台配置: {platfrom_name}")
        return False
    
    login_url = config.get('LOGIN_PAGE_URL')
    username = config.get('USERNAME')
    password = config.get('PASSWORD')
    
    if not username or not password:
        print(f"❌ 平台 {platfrom_name} 缺少配置")
        return False
    
    print(f"\n开始登录: {platfrom_name}")
    
    # 确保 cookies 文件夹存在
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR)
    options = Options()
    options.add_argument("--headless")
    #options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(
        service=Service("C:/Users/wsmian/Desktop/用户资金-流失/用户资金-流失/session/chromedriver.exe"),
        options=options
    )

    try:
        driver.get(login_url)
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "email_address"))
        )

        driver.find_element(By.NAME, "email_address").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)

        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "button"))
        )
        driver.execute_script("arguments[0].click();", button)

        WebDriverWait(driver, 15).until(
            EC.url_contains("dashboard")
        )
        
        print(f"✅ {platfrom_name} 登录成功")

        csrf_token = driver.execute_script("""return document.querySelector('meta[name="csrf-token"]').getAttribute('content')""")

        cookies = driver.get_cookies()
        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}

        cookies_dict['csrf_token'] = csrf_token

        cookies_file = os.path.join(COOKIES_DIR, f"cookies_{platfrom_name}.json")
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies_dict, f, indent=2, ensure_ascii=False)

        time.sleep(3)
        return True

    except Exception as e:
        print(f"❌ {platfrom_name} 登录失败: {e}")
        return False

    finally:
        driver.quit()

if __name__ == '__main__':
    platfrom = ['7ss','vana7','7luck','brlucky','7xx','7aa','brl77','novo7','sp7','b7','1xspin','b777','1xspin','spin77','sp1','bx365','brplay7','gana7','brslot','7pg','brspin','brwins','x7s']
    print(f"平台: {', '.join(platfrom)}\n")

    for i, platfrom_name in enumerate(platfrom, 1):
        print(f"\n[{i}/{len(platfrom)}] {platfrom_name}")
        success = login_and_save_profile(platfrom_name)
        if not  success:
            time.sleep(5)
            login_and_save_profile(platfrom_name)
        if i < len(platfrom):
            time.sleep(1)
    print(f"\n{'='*60}")
    print(f"全部平台登录态cookies已获取")
    print(f"{'='*60}\n")
