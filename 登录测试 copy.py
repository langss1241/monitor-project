import requests
import platfrom_config
from platfrom_config import get_platfrom_config
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import time
import get_cookies
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from zoneinfo import ZoneInfo

#0日志层
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_ROOT_DIR = os.path.join(BASE_DIR, "logs")

def write_log(message, platfrom_name=None, level="INFO"):
    day_dir = os.path.join(LOG_ROOT_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(day_dir, exist_ok=True)

    log_file = os.path.join(day_dir, f"{platfrom_name}.log" if platfrom_name else "runtime.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)

def log_print(message, platfrom_name=None, level="INFO"):
    print(message)
    write_log(message, platfrom_name=platfrom_name, level=level)

#1.抓取层，获取所有页数据
def fetch(platfrom_name,start_time, end_time):
    config = platfrom_config.get_platfrom_config(platfrom_name)
    if not config:
        log_print(f"❌ 未找到平台配置: {platfrom_name}", platfrom_name, "ERROR")
        return [], {}

    cookies_data = platfrom_config.get_platfrom_cookies(platfrom_name)
    authorization = (cookies_data or {}).get("authorization")
    if not authorization:
        log_print(f"❌ 平台 {platfrom_name} 缺少 Authorization,请先运行 get_cookies.py", platfrom_name, "ERROR")
        return [], {}

    url = config["user_url"]

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN",
        "agentflag": "0",
        "content-type": "application/json;charset=UTF-8",
        "Authorization": authorization,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "x-language": "CN"
    }

    def is_auth_invalid(response, body):
        if response.status_code in (401, 403):
            return True

        code = body.get("code")
        if code in (401, 403):
            return True

        message_text = str(body.get("msg") or body.get("message") or "").lower()
        auth_keywords = [
            "token",
            "authorization",
            "auth",
            "login",
            "未登录",
            "登录失效",
            "token失效",
            "请重新登录",
        ]
        return any(keyword in message_text for keyword in auth_keywords)

    def refresh_authorization(current_headers):
        log_print(f"[{platfrom_name}] 检测到认证失效，尝试刷新 cookies", platfrom_name)
        refreshed = get_cookies.login_and_save_profile(platfrom_name)
        if not refreshed:
            log_print(f"❌ [{platfrom_name}] 刷新 cookies 失败", platfrom_name, "ERROR")
            return False

        new_cookie_data = platfrom_config.get_platfrom_cookies(platfrom_name)
        new_authorization = (new_cookie_data or {}).get("authorization")
        if not new_authorization:
            log_print(f"❌ [{platfrom_name}] 刷新后未读取到 authorization", platfrom_name, "ERROR")
            return False

        current_headers["Authorization"] = new_authorization
        log_print(f"✅ [{platfrom_name}] 已更新 Authorization", platfrom_name)
        return True

    page = 1
    page_size = 100
    all_items = []
    max_pages = 1000

    while page <= max_pages:
        params = {
            "page": page,
            "pageSize": page_size,
            "uid": "",
            "user_mobile": "",
            "bank_account": "",
            "vip_level": "",
            "invite_code": "",
            "register_time[0]": start_time,
            "register_time[1]": end_time,
        }

        body = None
        for attempt in range(1, 6):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=20)
                log_print(f"[{platfrom_name}] page={page} attempt={attempt}/5 status={response.status_code}", platfrom_name)

                try:
                    body = response.json()
                except ValueError:
                    body = {}

                if is_auth_invalid(response, body):
                    if not refresh_authorization(headers):
                        if attempt == 5:
                            log_print(f"❌ [{platfrom_name}] 认证刷新失败，达到最大重试次数", platfrom_name, "ERROR")
                            return all_items, headers
                        time.sleep(1)
                        continue

                    time.sleep(1)
                    continue

                response.raise_for_status()
                break
            except Exception as exc:
                if attempt == 5:
                    log_print(f"❌ [{platfrom_name}] 抓取第 {page} 页失败（重试 5 次后）: {exc}", platfrom_name, "ERROR")
                    return all_items, headers
                log_print(f"⚠️ [{platfrom_name}] 抓取第 {page} 页异常，第 {attempt} 次重试: {exc}", platfrom_name, "WARNING")
                time.sleep(1)

        if body is None:
            log_print(f"❌ [{platfrom_name}] 第 {page} 页无有效响应，分页结束", platfrom_name, "ERROR")
            break

        data = body.get("data") or {}
        items = data.get("items") or []
        page_info = data.get("pageInfo") or {}

        if not items:
            log_print(f"[{platfrom_name}] 第 {page} 页无数据，分页结束", platfrom_name)
            break

        all_items.extend(items)

        total_page = page_info.get("totalPage")
        current_page = page_info.get("page", page)
        total_count = page_info.get("total")
        log_print(f"[{platfrom_name}] 已抓取 page {current_page}/{total_page or '?'}，当前累计 {len(all_items)} 条，总数 {total_count}", platfrom_name)

        #判断结束条件

        if total_page and current_page >= total_page:
            log_print(f"[{platfrom_name}] 已到最后一页", platfrom_name)
            break

        if len(items) < page_size:
            log_print(f"[{platfrom_name}] 本页不足 pageSize，视为最后一页", platfrom_name)
            break

        page += 1
        time.sleep(0.1)

    return all_items, headers


#3.解析层
def  load_json(all_items):
    def  is_empty_order_time(value):
        return value is  None or str(value).strip() == ""

    zero_order_members = [m for m  in all_items if  is_empty_order_time(m.get("order_time"))]   #推导真棒

    uid_list = [m.get("uid") for m in zero_order_members]

    length = len(uid_list)

    return uid_list, length


#5.站内信组装层
def send_message_to_members(platfrom_name,headers,uid_list):

    #配置
    params_tem = get_platfrom_config(platfrom_name)['params_m']

    params_m = copy.deepcopy(params_tem)

    # uid 之间逗号拼接
    params_m["receive_uids"] = ",".join(map(str, uid_list))

    mess_url = get_platfrom_config(platfrom_name)['mess_url']

    for attempt in range(1, 4):
        try:
            resonse = requests.post(mess_url, headers=headers, params=params_m,timeout=20)
            if resonse.status_code == 200:
                log_print(f"✅ [{platfrom_name}] 站内信组装成功", platfrom_name)

                body = resonse.json()
                data = body.get("data", {})
                id = data.get("id")
                params_m["task_id"],params_m["taskId"] = id,id
               

                receive_uids = params_m["receive_uids"]

                return receive_uids, id, params_m
            else:
                log_print(f"⚠️ [{platfrom_name}] 站内信发送失败，状态码: {resonse.status_code}", platfrom_name, "WARNING")
        except Exception as e:
            log_print(f"⚠️ [{platfrom_name}] 站内信发送异常，第 {attempt} 次重试: {e}", platfrom_name, "ERROR")

        if attempt < 3:
            time.sleep(1.5)  # 重试间隔

def send_now(platfrom_name,headers,id,params_m):

    send_mess_url = get_platfrom_config(platfrom_name)['send_mess_url'] + str(id)

    send_payload = copy.deepcopy(params_m) if params_m else {}
    send_payload.setdefault("award_type", "1")
    send_payload.setdefault("receive_type", "3")
    send_payload.setdefault("mail_type", 1)
    send_payload["end_send_time"] = send_payload.get("end_send_time") or send_payload.get("end_send_time_1") or ""
    send_payload["task_id"] = send_payload.get("task_id") or send_payload.get("taskId") or 0
    send_payload["taskId"] = send_payload["task_id"]
    send_payload["id"] = id

    send_headers = headers.copy()
    # 对齐浏览器成功请求：PUT + application/json
    send_headers["content-type"] = "application/json;charset=UTF-8"
    send_headers["accept-language"] = "zh_CN"

    for attempt in range(1, 4):
        try:
            resonse = requests.put(send_mess_url, headers=send_headers, json=send_payload, timeout=20)

            if resonse.status_code == 200:
                log_print(f"✅ [{platfrom_name}] 站内信发送成功", platfrom_name)
                return True

            log_print(
                f"⚠️ [{platfrom_name}] 发送失败 (PUT)，状态码: {resonse.status_code}，"
                f"响应: {resonse.text[:300]}",
                platfrom_name,
                "WARNING"
            )
        except Exception as e:
            log_print(f"⚠️ [{platfrom_name}] 站内信发送异常，第 {attempt} 次重试: {e}", platfrom_name, "ERROR")

        if attempt < 3:
            time.sleep(1.5)  # 重试间隔

    return False


#6.飞机及日志层
def send_tg(platfrom_name, length, receive_uids, end_time_in,id) -> dict:

    bot_token = '8800598379:AAF5W-k_hsYTuyOj7oB3LvdHKCdlj9OkD70'

    #chat_id = '-5360423276'
    chat_id = '-5191495280'  # 测试


    # tg消息
    now = end_time_in.strftime("%m%d-%H:%M")   #窗口截至时间
    
    if length > 0:
        uid_parts = [x.strip() for x in str(receive_uids).split(",") if x.strip()]
        top3_uids = ",".join(uid_parts[:3])

        message = f"📩【{platfrom_name}】近5~10min 注册未充值.{now}\n\n共 {length} 人 已发站内信     【配置id】{id} \n\n{top3_uids}.."

    else:
        return

    if not bot_token:
        return {"ok": False, "error": "bot_token 为空"}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True
    }

    for i in range(1, 4):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            
            if data.get("ok"):
                return {"ok": True, "result": data.get("result")}
            else:
                error_msg = data.get("description", "未知错误")
                log_print(f"[{platfrom_name}] 第 {i} 次TG发送失败: {error_msg}", platfrom_name, "WARNING")
                
        except Exception as e:
            log_print(f"[{platfrom_name}] 第 {i} 次TG发送异常: {e}", platfrom_name, "ERROR")
        
        if i < 3:
            time.sleep(1.5)  # 重试间隔

    return {"ok": False, "error": "发送失败，已达最大重试次数"}

#7.编排层
def run_platform(platfrom_name, start_time, end_time, end_time_in):
    log_print(f"正在处理平台: {platfrom_name}", platfrom_name)

    all_items, headers = fetch(platfrom_name, start_time, end_time)
    log_print(f"[{platfrom_name}] 本次分页抓取总数: {len(all_items)}", platfrom_name)

    uid_list, length = load_json(all_items)
    log_print(f"[{platfrom_name}] 注册未充值会员: {length}", platfrom_name)

    if length <= 0:
        log_print(f"[{platfrom_name}] 无需发送站内信", platfrom_name)
        return

    result = send_message_to_members(platfrom_name, headers, uid_list)
    if not result:
        log_print(f"❌ [{platfrom_name}] 站内信组装失败，跳过", platfrom_name, "ERROR")
        return

    receive_uids, id, params_m = result
    time.sleep(2)  # 等待站内信组装完成

    sent_ok = send_now(platfrom_name, headers, id, params_m)
    if not sent_ok:
        log_print(f"❌ [{platfrom_name}] send_now 失败，跳过 TG", platfrom_name, "ERROR")
        return

    tg_result = send_tg(platfrom_name, length, receive_uids, end_time_in, id)
    if not tg_result or not tg_result.get("ok"):
        log_print(f"❌ [{platfrom_name}] TG发送失败: {tg_result}", platfrom_name, "ERROR")
        return

    log_print(f"✅ [{platfrom_name}] 处理完成\n{'-'*50}\n", platfrom_name)


def main(start_time, end_time,end_time_in):
    platforms = ['ik7']

    with ThreadPoolExecutor(max_workers=len(platforms)) as executor:
        futures = {
            executor.submit(run_platform, p, start_time, end_time, end_time_in): p
            for p in platforms
        }
        for future in as_completed(futures):
            platfrom_name = futures[future]
            try:
                future.result()
            except Exception as exc:
                log_print(f"❌ [{platfrom_name}] 并发任务异常: {exc}", platfrom_name, "ERROR")

if __name__ == "__main__":
    while True:
        # 本机泰国时间(UTC+7) -> 服务器印度时间(UTC+5:30)
        th_tz = ZoneInfo("Asia/Bangkok")  # 泰国时间
        in_tz = ZoneInfo("Asia/Kolkata")  # 印度时间

        start_loop = datetime.now(th_tz)

        end_time_in = datetime.now(th_tz).astimezone(in_tz) - timedelta(minutes=5)
        #end_time_in = datetime(2026, 8, 8, 12, 0, 0, tzinfo=in_tz)

        start_time_in = end_time_in - timedelta(minutes=5)

        end_time = end_time_in.strftime("%Y-%m-%d %H:%M:%S")
        start_time = start_time_in.strftime("%Y-%m-%d %H:%M:%S")

        log_print(f"本次查询窗口(印度时间): {start_time} ~ {end_time}")

        try:
            main(start_time, end_time,end_time_in)
        except Exception as e:
            log_print(f"❌ [sh7] 本轮处理异常: {e}", "sh7", "ERROR ")
        finally:
            log_print("本轮完成,下一轮等待执行...")

            next_run = start_loop + timedelta(minutes=5)

            sleep_seconds = (next_run - datetime.now(th_tz)).total_seconds()

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)  # 每 5 分钟执行一次
        