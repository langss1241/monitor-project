# -*- coding: utf-8 -*-
import json
import os
from platform import platform


PLATFROM_CONFIGS = {
    'betroia': {
    'USERNAME': 'TOPChunk',
    'PASSWORD': 'AAAA1111!',
    'TOTP_SECRET': '7DFD57AA57AF65GB',
    'LOGIN_PAGE_URL': 'https://boss.betroiawbwz.top/login',
    'SESSION_URL': 'https://boss.betroiawbwz.top/dashboard/dashboardIndex',
    'OP_URL': 'https://boss.betroiawbwz.top/op/flexReport/control/query/NA.QueryByReport'
    },
   'afun-mx': {
    'USERNAME': 'TOPChunk',
    'PASSWORD': 'AAAA1111!',
    'TOTP_SECRET': '7DFD57AA57AF65GB',
    'LOGIN_PAGE_URL': 'https://boss.sky92wjs.online',
    'SESSION_URL': 'https://boss.sky92wjs.online/dashboard/dashboardIndex',
    'OP_URL': 'https://boss.sky92wjs.online/op/flexReport/control/query/NA.QueryByReport',
    },
    'soluno': {
    'USERNAME': 'TOPChunk',
    'PASSWORD': 'AAAA1111!',
    'TOTP_SECRET': '7DFD57AA57AF65GB',
    'LOGIN_PAGE_URL': 'https://boss.solunobsjdn32ewd.work',
    'SESSION_URL': 'https://boss.solunobsjdn32ewd.work/dashboard/dashboardIndex',
    'OP_URL': 'https://boss.solunobsjdn32ewd.work/op/flexReport/control/query/NA.QueryByReport'

    },
    'sol777': {
    'USERNAME': 'TOPChunk',
    'PASSWORD': 'AAAA1111!',
    'TOTP_SECRET': '7DFD57AA57AF65GB',
    'LOGIN_PAGE_URL': 'https://boss.sol7hdjaaa.work',
    'SESSION_URL': 'https://boss.sol7hdjaaa.work/dashboard/dashboardIndex',
    'OP_URL': 'https://boss.sol7hdjaaa.work/op/flexReport/control/query/NA.QueryByReport'

            },
    'lucro': {
        'USERNAME': 'TOPChunk',
        'PASSWORD': 'AAAA1111!',
        'TOTP_SECRET': '7DFD57AA57AF65GB',  
        'LOGIN_PAGE_URL': 'https://boss.lucrosidfksj.top',
        'SESSION_URL': 'https://boss.lucrosidfksj.top/dashboard/dashboardIndex',
        'OP_URL': 'https://boss.lucrosidfksj.top/op/flexReport/control/query/NA.QueryByReport'
    },
    'oro7x': {
        'USERNAME': 'TOPChunk',
        'PASSWORD': 'AAAA1111!',
        'TOTP_SECRET': '7DFD57AA57AF65GB',
        'LOGIN_PAGE_URL': 'https://boss.oro7xwbwz.top',
        'SESSION_URL': 'https://boss.oro7xwbwz.top/dashboard/dashboardIndex',
        'OP_URL': 'https://boss.oro7xwbwz.top/op/flexReport/control/query/NA.QueryByReport'
    }
    ,
    'afun-br': {
        'USERNAME': 'TOPChunk',
        'PASSWORD': 'AAAA1111!',
        'TOTP_SECRET': '7DFD57AA57AF65GB',
        'LOGIN_PAGE_URL': 'https://boss.uu88sdn.online',
        'SESSION_URL': 'https://boss.uu88sdn.online/dashboard/dashboardIndex',
        'OP_URL': 'https://boss.uu88sdn.online/op/flexReport/control/query/NA.QueryByReport'
    }
   
}


def get_platfrom_config(platfrom_name):
    return PLATFROM_CONFIGS.get(platfrom_name)


def get_platfrom_cookies(platfrom_name):
    """从 JSON文件读取平台 Cookie"""
    cookies_file = f"/home/bi/home/project/monitor/质检每日/session/cookie_{platfrom_name}.json"
    if not os.path.exists(cookies_file):
        return None
    
    try:
        with open(cookies_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None