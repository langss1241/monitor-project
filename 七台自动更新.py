import requests
import base64
import json
import csv
import os
import time
from Cryptodome.Cipher import AES
from bs4 import BeautifulSoup
import datetime
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import platfrom_config
from platfrom_config import get_platfrom_config,get_platfrom_cookies
import get_token
from get_token import login_backend
from pathlib import Path
import logging


#全局配置
REPORT_TZ = ZoneInfo("America/Mexico_City")     
ARMENIA_TZ = ZoneInfo("Asia/Yerevan")

yesterday = datetime.now(REPORT_TZ).date() - timedelta(days=1)
previous_day = yesterday - timedelta(days=1)
s_time = int(datetime.combine(previous_day, datetime.min.time(), tzinfo=REPORT_TZ).timestamp())
e_time = int(datetime.combine(yesterday, datetime.min.time(), tzinfo=REPORT_TZ).replace(hour=23, minute=59, second=59).timestamp())


print(datetime.now(REPORT_TZ),s_time,e_time)

print(f"e_time: {e_time}, s_time: {s_time}")

#logging 层
class Logge:
    def __init__(self):
        path = Path(__file__).resolve().parent / "logge"
        path.mkdir(exist_ok=True)
        self.file = open(path / "run.log", "a", encoding="utf-8")

    def write(self, msg):
        self.file.write(f"[{datetime.now(REPORT_TZ):%Y-%m-%d %H:%M:%S}] {msg}\n")
        self.file.flush()

logge = Logge()   #初始化

#通信层
def send_lark(report_file):
    webhook = "https://open.larksuite.com/open-apis/bot/v2/hook/b7e3e0bb-24d7-4db6-b13e-64a25532f051"

    with report_file.open("r", encoding="utf-8") as f:
        report = f.read()

    res = requests.post(webhook, json={"msg_type": "text", "content": {"text": report}}, timeout=10)     

    res.raise_for_status()
    print(f"报告已发送到飞书群: {report_file.name}")
    logge.write(f"报告已发送到飞书群: {report_file.name}")


#请求头
def build_headers(platfrom_name):
    cookie_data = get_platfrom_cookies(platfrom_name)
    auth_headers = cookie_data or {}
    token = auth_headers.get("token")
    device = auth_headers.get("device")
    if not token or not device:
        print(f"未找到 {platfrom_name} 的完整认证信息，请重新运行 get_{platfrom_name}_token.py")
        logge.write(f"未找到 {platfrom_name} 的完整认证信息，请重新运行 get_{platfrom_name}_token.py")
        exit(1)

    headers = {
        "accept": "*/*",
        "accept-language": "zh,zh-CN;q=0.9",
        "content-type": "application/json",
        "token": token,
        "device": device,
        # "origin": "https://boss.betroiawbwz.top",
        "lang": "0",
        "os-type": "1",
        # "referer": auth_headers.get("referer") or "https://boss.betroiawbwz.top/data-center/pingtaibaobiao/693c47554b3f05b929172f7e",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    }

    if auth_headers.get("cookie"):
        headers["cookie"] = auth_headers["cookie"]


    timestamp = int(time.time())
    sign_data = f"device={headers['device']}&timestamp={timestamp}".encode()
    sign_data += b"\0" * (-len(sign_data) % 16)
    cipher = AES.new(b"E8aTO43VgyMeFZUw", AES.MODE_CBC, b"PWeJViG1mum5DmJ1")
    headers["sign"] = base64.b64encode(cipher.encrypt(sign_data)).decode()
    
    return headers


def claw_op_v2(platfrom_name,headers) -> list[dict]:

    headers = build_headers(platfrom_name)

    URL = get_platfrom_config(platfrom_name)["OP_URL"]

    payload = {
        "website": 1,
        "coin": "USD",
        "report_config_id": "693c47554b3f05b929172f7e",
        "plat_id": "999",
        "app_id": "999",
        "page": 1,
        "page_size": 30,
        "filter": {
            "report_name": "平台报表",
            "e_time": e_time,
            "s_time": s_time,
            "filter_list": [
                {
                    "column": "general_no",
                    "value": "",
                    "operator": "in",
                    "is_dim": True
                }
            ]
        }
    };


    res = requests.post(
        url=URL,
        json=payload,
        headers=headers,
        timeout=30,
    )

    print(res.status_code)

    #更新token
    if res.status_code in (401, 403):
        print(f"接口请求失败 ({res.status_code})：{res.text[:500]}")
        logge.write(f"接口请求失败 ({res.status_code})：{res.text[:500]}")
        logge.write(f"尝试重新登录获取新的 token...")
        get_token.login_backend(platfrom_name)
        headers = build_headers(platfrom_name)

        
        res = requests.post(
        url=URL,
        json=payload,
        headers=headers,
        timeout=30)

        print(res.status_code)

    try:
        response_data = res.json()
    except ValueError as error:
        raise RuntimeError(f"接口返回了非 JSON 响应：{res.text[:500]}") from error
        logge.write(f"接口返回了非 JSON 响应：{res.text[:500]}")

    # if res.status_code >= 400:
    #     raise RuntimeError(f"接口请求失败 ({res.status_code})：{response_data}")
    # if not isinstance(response_data, dict) or "_param" not in response_data:
    #     raise RuntimeError(f"接口没有返回报表数据：{response_data}")

    data = response_data["_param"].get("list")
    if not isinstance(data, list):
        raise RuntimeError(f"报表响应缺少有效的 list：{response_data['_param']}")
        logge.write(f"报表响应缺少有效的 list：{response_data['_param']}")
    
    return data


def report(platfrom_name,data):
    data_dir = Path(__file__).resolve().parent / "data"
    report_dir = Path(__file__).resolve().parent / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    data_file = data_dir / f"{platfrom_name}_data_{yesterday.strftime('%Y%m%d')}.json"
    report_file = report_dir / f"report_{yesterday.strftime('%Y%m%d')}.txt"


    #写入 JSON 文件
    with data_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


    rows = {int(row["day_time"]): row for row in data}
    yesterday_key = int(yesterday.strftime("%Y%m%d"))
    previous_key = int(previous_day.strftime("%Y%m%d"))

    if yesterday_key not in rows or previous_key not in rows:
        print(f"报表缺少昨天或前天的数据：{yesterday_key}, {previous_key}")
        logge.write(f"报表缺少昨天或前天的数据：{yesterday_key}, {previous_key}")
    else:
        today_data = rows[yesterday_key]
        previous_data = rows[previous_key]

        def number(row, key):
            return float(str(row.get(key, "0")).replace(",", "").replace("%", ""))

        def change(key):
            current = number(today_data, key)
            previous = number(previous_data, key)
            if previous == 0:
                return "较昨日无可比数据"
            percent = (current - previous) / abs(previous) * 100
            if percent > 0:
                direction = "增长"
            elif percent < 0:
                direction = "下降"
            else:
                return "较昨日持平"
            return f"较昨日{direction}{abs(percent):.2f}%"

        def count(key):
            return f"{number(today_data, key):,.0f}人"

        def amount(key):
            return f"{number(today_data, key) / 10000:.2f}万"

        def rate(key):
            return f"{number(today_data, key):.2f}%"

        report = (
            f"{platfrom_name} **{yesterday.month}/{yesterday.day}** "
            f"注册人数**{count('today_register_count')}**，{change('today_register_count')}；"
            f"活跃人数**{count('active_num')}**，{change('active_num')}；"
            f"首充人数**{count('new_first_recharge_count')}**，{change('new_first_recharge_count')}；"
            f"首充转化率**{rate('today_register_first_pay_ratio')}**，{change('today_register_first_pay_ratio')}；"
            f"充值金额**{amount('today_pay_sum')}**，{change('today_pay_sum')}；"
            f"活跃用户付费率**{rate('active_pay_rate')}**，{change('active_pay_rate')}；"
            f"充提差**{amount('pay_put_sum')}**，{change('pay_put_sum')}；"
            f"充提差比**{rate('pay_put_spread_pct')}**，{change('pay_put_spread_pct')}；"
            f"投注金额**{amount('today_bet_sum')}**，{change('today_bet_sum')}；"
            f"公司盈利**{amount('today_profit')}**，{change('today_profit')}。"
        )
        print(report)

    #写入报告   
    with report_file.open("a", newline="", encoding="utf-8") as f:
        f.write(report + "\n\n")
    print(f"{platfrom_name} 报告已写入 {report_file.name}")
    logge.write(f"{platfrom_name} 报告已写入 {report_file.name}")

    return report_file


def main():
    for platfrom_name in  platfrom_config.PLATFROM_CONFIGS.keys():
        try:
            headers=build_headers(platfrom_name)  # 构建请求头
            data = claw_op_v2(platfrom_name,headers)
            if data:
                report_file = report(platfrom_name,data)
        except Exception as e:
            print(f"处理 {platfrom_name} 时出错: {e}")
            logge.write(f"处理 {platfrom_name} 时出错: {e}")
    
    print('daole')

    send_lark(report_file)
                

if __name__ == "__main__":
    while True:
        now = datetime.now(ARMENIA_TZ)

        next_run = now.replace(hour=11, minute=6, second=0, microsecond=0)

        if next_run <= now:
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        print(f"下次运行时间（亚美尼亚时间）: {next_run:%Y-%m-%d %H:%M:%S}")
        logge.write(f"下次运行时间（亚美尼亚时间）: {next_run:%Y-%m-%d %H:%M:%S}")
        logge.write(f"等待 {wait_seconds:.0f} 秒后运行...")
        print(f"等待 {wait_seconds:.0f} 秒后运行...")
        time.sleep(wait_seconds)
        main()


    