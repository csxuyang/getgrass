import asyncio
import time
import json
import ssl
import uuid
import random
import logging
from websockets_proxy import Proxy, proxy_connect
from faker import Faker
import websockets


# 配置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def send_message(websocket, message):
    """
    发送消息到 WebSocket 服务器
    """
    message_str = json.dumps(message)
    logging.info(f"Sending message: {message_str}")
    await websocket.send(message_str)


async def receive_message(websocket):
    """
    接收 WebSocket 服务器的消息
    """
    response = await websocket.recv()
    logging.info(f"Received response: {response}")
    return json.loads(response)


async def authenticate(websocket, auth_id, device_id, user_id):
    """
    发送认证消息到 WebSocket 服务器
    """
    auth_message = {
        "id": auth_id,
        "origin_action": "AUTH",
        "result": {
            "browser_id": device_id,
            "user_id": user_id,
            "user_agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            "timestamp": int(time.time()),
            "device_type": "extension",
            "version": "2.5.0"
        }
    }
    await send_message(websocket, auth_message)


async def run_websocket_logic(websocket, user_id, device_id):
    """
    业务逻辑处理
    """
    # 第1步：发送auth请求
    message = {
        "id": str(uuid.uuid4()),
        "version": "1.0.0",
        "action": "PING",
        "data": {}
    }
    await send_message(websocket, message)
    # 第2步：接收平台auth请求响应
    auth_response = await receive_message(websocket)

    await asyncio.sleep(random.randint(10, 20) / 10)
    # 第3步：进行auth请求
    await authenticate(websocket, auth_response["id"], device_id, user_id)
    while True:
        # 第4步：得到认证成功请求响应
        pong_response = await receive_message(websocket)
        logging.info(f"pong_response: {pong_response} ")
        await asyncio.sleep(random.randint(1, 9) / 10)
        pong_message = {
            "id": pong_response["id"],
            "origin_action": "PONG"
        }
        # 第5步：回复平台已得到认证成功请求响应
        await send_message(websocket, pong_message)

        await asyncio.sleep(random.randint(180, 250) / 10)

        ping_message = {
            "id": str(uuid.uuid4()),
            "version": "1.0.0",
            "action": "PING",
            "data": {}
        }
        # 第6步：发送心跳包
        await send_message(websocket, ping_message)
        await asyncio.sleep(random.randint(1, 9) / 10)



async def run_with_proxy(uri, ssl_context, custom_headers, device_id, user_id, proxy):
    """
    使用代理运行 WebSocket 连接
    """
    try:
        async with proxy_connect(uri, ssl=ssl_context, extra_headers=custom_headers, proxy=proxy, proxy_conn_timeout=10) as websocket_p:
            await run_websocket_logic(websocket_p, user_id, device_id)
    except Exception as e:
        logging.error(f"Error occurred with proxy {proxy.proxy_host}: {proxy.proxy_port} {e}")

async def run_without_proxy(uri, ssl_context, custom_headers, device_id, user_id):
    """
    不使用代理运行 WebSocket 连接
    """
    try:
        async with websockets.connect(uri, ssl=ssl_context, extra_headers=custom_headers) as websocket:
            await run_websocket_logic(websocket, user_id, device_id)
    except Exception as e:
        logging.error(f"Error occurred without proxy  {e}")


async def main(user_id, use_proxy, proxies=None):
    """
    主函数
    """
    uri_options = ["wss://proxy.wynd.network:4650/", "wss://proxy.wynd.network:4444"]
    custom_headers = {
        "User-Agent": Faker().chrome()
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    tasks = []
    device_id = str(uuid.uuid4())
    logging.info(device_id)

    loop = asyncio.get_event_loop()
    if use_proxy:
        for proxy in proxies:
            for uri in uri_options:
                tasks.append(run_with_proxy(uri, ssl_context, custom_headers, device_id, user_id, proxy))
    else:
        for uri in uri_options:
            tasks.append(run_without_proxy(uri, ssl_context, custom_headers, device_id, user_id))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    user_id = '5b62d235-273c-4707-85df-9bcca26a5306'
    use_proxy = False  # 设置为 True 则使用代理，False 则不使用
    # 账号密码模式 'socks5://username:password@address:port'
    # 无密码模式 'socks5://address:port'
    proxies = [Proxy.from_url("socks5://192.168.124.20:1082"),Proxy.from_url("socks5://udk390:32384@182.44.113.41:16790")]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(user_id, use_proxy, proxies))
