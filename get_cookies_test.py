#登录获取cookies
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
from datetime import datetime
from platfrom_config import get_platfrom_config
import pyotp

COOKIES_DIR = "/home/bi/home/project/monitor/质检每日/session"  # 指定 cookies 文件夹路径

def get_authorization_from_logs(driver):
    latest_auth = None

    try:
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"]).get("message", {})
            method = message.get("method")

            if method not in ("Network.requestWillBeSentExtraInfo", "Network.requestWillBeSent"):
                continue

            params = message.get("params", {})
            headers = params.get("headers", {})

            for key, value in headers.items():
                if key.lower() != "authorization":
                    continue

                auth_value = str(value).strip()
                if auth_value.lower() in {
                    "",
                    "null",
                    "undefined",
                    "bearer null",
                    "bearer undefined",
                }:
                    continue

                latest_auth = auth_value
    except Exception as exc:
        print(f"抓取 Authorization 失败: {exc}")

    return latest_auth

def find_verify_input(driver):
    """验证码框通常是剩下的那个可见文本框，不依赖 placeholder。"""
    text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
    for el in reversed(text_inputs):
        if not el.is_displayed():
            continue
        placeholder = (el.get_attribute("placeholder") or "").strip()
        aria_label = (el.get_attribute("aria-label") or "").strip()
        if placeholder in {"账户", "账号", "密码"}:
            continue
        if aria_label in {"账户", "账号", "密码"}:
            continue
        return el
    raise TimeoutError("未找到验证码输入框")


def login_and_save_profile(platfrom_name):
    """登录指定平台并保存cookies"""
    config = get_platfrom_config(platfrom_name)
    if not config:
        print(f"❌ 未找到平台配置: {platfrom_name}")
        return False
    
    login_url = config.get('LOGIN_PAGE_URL')
    username = config.get('USERNAME')
    password = config.get('PASSWORD')
    verify_key = config.get('google_key')   
    verify_code = pyotp.TOTP(verify_key).now()
    print(f"验证码: {verify_code} (基于密钥: {verify_key})")

    if not username or not password:
        print(f"❌ 平台 {platfrom_name} 缺少配置")
        return False
    
    print(f"\n开始登录: {platfrom_name}")
    
    # 确保 cookies 文件夹存在
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR)

    options = Options()
    #options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as exc:
        print(f"❌ Chrome 启动失败: {exc}")
        return False

    try:
        print(f"浏览器已启动，正在打开: {login_url}")
        driver.get(login_url)

        #印度盘
        username_placeholder = "账号" if platfrom_name == "sh7" else "账户"

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                f"input[placeholder='{username_placeholder}']"
            ))
        )

        username_input = driver.find_element(
            By.CSS_SELECTOR,
            f"input[placeholder='{username_placeholder}']"
        )

        password_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='密码']")

        if platfrom_name == "sh7":
            verify_input = driver.find_element(
                By.CSS_SELECTOR,
                "input[placeholder='谷歌验证码']"
            )
        else:
            verify_input = find_verify_input(driver)

        username_input.clear()
        username_input.send_keys(username)

        password_input.clear()
        password_input.send_keys(password)

        verify_input.clear()
        verify_input.send_keys(verify_code)

        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "button.arco-btn.arco-btn-primary[type='submit'], button[type='submit']"
            ))
        )
        if "登录" not in button.text:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(normalize-space(.), '登录')]"))
            )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
        time.sleep(0.5)
        try:
            button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", button)

        try:
            home_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[@type='button' and contains(normalize-space(.), '回到首页')]"
                ))
            )
            home_button.click()
            print("已点击 回到首页")
        except Exception:
            pass
 
        print(f"✅ {platfrom_name} 登录成功")
        time.sleep(1)  # 等待页面加载完成

        try:
            profile_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//span[contains(@class, 'arco-menu-title') and normalize-space(.)='个人信息']"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", profile_button)
            time.sleep(0.5)
            profile_button.click()
            print("已点击 个人信息")
        except Exception:
            print("未找到 个人信息 按钮，跳过")

        time.sleep(2)  # 等待页面加载完成


        # 获取 Authorization 并保存到 JSON 文件

        authorization = get_authorization_from_logs(driver)


        print("抓到的 Authorization:", authorization)

        save_data = {
            "authorization": authorization
        }

        cookies_file = os.path.join(COOKIES_DIR, f"cookies_{platfrom_name}.json")

        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        print(f"已保存: {cookies_file}")

        time.sleep(3)
        return True

    except Exception as e:
        print(f"❌ {platfrom_name} 登录失败: {e}")
        return False

    finally:
        driver.quit()

if __name__ == "__main__":
    platfrom_name = None
    # #main(platfrom)  # 
    # # for platfrom_name in ["dhan7", "raja7", "ek1"]:
    # #     print(f"正在处理平台: {platfrom_name}")
    #login_and_save_profile('sh7')
    for attempt in range(4):
        if not login_and_save_profile(platfrom_name):
            print(f"第 {attempt + 1} 次尝试失败")
            time.sleep(5)  
        else:
            print(f"第 {attempt + 1} 次尝试成功")
            break
