import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pyotp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import platfrom_config
from platfrom_config import get_platfrom_config
import requests


USERNAME = "TOPChunk"
PASSWORD = "AAAA1111!"
TOTP_SECRET = "7DFD57AA57AF65GB"
ARMENIA_TZ = ZoneInfo("Asia/Yerevan")


def get_auth_headers_from_logs(driver):
    for entry in driver.get_log("performance"):
        message = json.loads(entry["message"]).get("message", {})
        params = message.get("params", {})
        request = params.get("request", {})
        headers = params.get("headers") or request.get("headers", {})
        normalized_headers = {name.lower(): value for name, value in headers.items()}
        token = normalized_headers.get("token")
        device = normalized_headers.get("device")
        cookie = normalized_headers.get("cookie")
        if token and device and cookie:
            return {
                "token": str(token).strip(),
                "device": str(device).strip(),
            "cookie": str(cookie).strip(),
                "page-title": normalized_headers.get("page-title", ""),
                "referer": normalized_headers.get("referer", ""),
                "user-agent": normalized_headers.get("user-agent", ""),
            }
    return None


def login_backend(platfrom_name):
    config = get_platfrom_config(platfrom_name)
    if not config:
        print(f"找不到后台配置: {platfrom_name}")
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    browser = webdriver.Chrome(options=options)

    step = "打开登录页"
    try:
        browser.get(config["LOGIN_PAGE_URL"])
        wait = WebDriverWait(browser, 20)
        step = "等待账号输入框"
        username_input = wait.until(EC.visibility_of_element_located((
            By.CSS_SELECTOR, "input[placeholder*='账号'], input[placeholder*='账户']"
        )))
        step = "查找密码输入框"
        browser.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(PASSWORD)
        step = "查找验证码输入框"
        browser.find_element(By.CSS_SELECTOR, "input[placeholder*='验证码']").send_keys(
            pyotp.TOTP(TOTP_SECRET).now()
        )
        username_input.send_keys(USERNAME)
        step = "等待登录按钮并点击"
        wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[translate(normalize-space(.), ' ', '')='登录']"
        ))).click()
        step = "等待登录后跳转"
        wait.until(lambda current: "/login" not in current.current_url)

        step = "读取登录请求中的认证请求头"
        auth_headers = None
        deadline = time.time() + 20
        while time.time() < deadline and not auth_headers:
            auth_headers = get_auth_headers_from_logs(browser)
            if not auth_headers:
                time.sleep(1)

        if not auth_headers:
            raise RuntimeError("没有从同一条后台请求中找到 token、device 和 cookie")

        session_dir = Path(__file__).resolve().parent / "session"
        session_dir.mkdir(parents=True, exist_ok=True)
        token_file = session_dir / f"cookie_{platfrom_name}.json"
        with token_file.open("w", encoding="utf-8") as file:
            json.dump(auth_headers, file, ensure_ascii=False, indent=2)
        print(f"{platfrom_name} 认证请求头已保存: {token_file.name}")
    except Exception as error:
        print(f"{platfrom_name} 在【{step}】失败 ({type(error).__name__}): {error}")
    finally:
        browser.quit()


def login_backend_with_retries(platfrom_name, max_attempts=4, delay=2):
    for attempt in range(max_attempts):
        try:
            login_backend(platfrom_name)
            break
        except Exception as error:
            print(f"尝试 {attempt + 1} 登录失败: {error}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                print("多次尝试登录失败，请检查网络和配置。")


def run_login():
    for platfrom_name in platfrom_config.PLATFROM_CONFIGS.keys():
        try:
            login_backend_with_retries(platfrom_name)
        except Exception as error:
            print(f"{platfrom_name} 登录任务异常: {error}")



if __name__ == "__main__":
    run_login()
