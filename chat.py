"""
by LUMO_Xu uid:66970100

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import openai
import os
import re
import random
import json
import requests

blue_color = '\033[0;34m'
cyan_color = '\033[0;36m'
end_color = '\033[0m'


def get_prompt(raw_record: list, fans_mode: bool or int):
    chatter_list = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'[::-1])
    trans_list = []
    sender_letter = {-1: '你', bot_qq: '你'}
    for one_record in raw_record:
        sender = one_record[0]
        msg = one_record[1]
        nickname = one_record[3]
        if sender not in sender_letter.keys():
            sender_letter[sender] = chatter_list.pop()
        if not fans_mode:
            trans_list.append(f'{sender_letter[sender]}: {msg}')
        else:
            trans_list.append(f'{nickname}: {msg}')

    res = '\n'.join(trans_list)
    res += '\n你: ?'
    return res



def answer(chat_rec, prompt=None):
    global api_key, proxy, api_endpoint
    openai.api_key = api_key
    openai.api_endpoint = api_endpoint
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy
    # 提问
    if prompt is None:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            prompt = f.read()

    # 访问OpenAI接口
    print('Ready to answer...')

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": chat_rec}
    ]

    request_data = {
        'messages': messages
    }

    response = requests.post(api_endpoint, headers={'Authorization': f'Bearer {api_key}'}, json=request_data)
    response = response.json()
    res = response['choices'][0]['message']['content']
    total_tokens = response['usage']['total_tokens']
    print(f'bot回复: {res}  (Tokens used: {total_tokens})')
    return res



def describe_image(ocr_text):
    global api_key, proxy, api_endpoint
    openai.api_key = api_key
    openai.api_endpoint = api_endpoint
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy

    print('ready to describe image...')
    prompt = '我会给你一张图片经ocr后识别出来的图片文字，其中可能包含各种杂乱文字，空格与符号。请你根据这些文字还原图片中最主要的信息，并将其精简到80字以内作为输出，使用简体中文输出。'
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": chat_rec}
    ]

    request_data = {
        'messages': messages
    }

    response = requests.post(api_endpoint, headers={'Authorization': f'Bearer {api_key}'}, json=request_data)

    res = response.choices[0].message.content
    total_tokens = response['usage']['total_tokens']
    print(blue_color + f'图片内容: {res}  ' + f'(Tokens used: {total_tokens})' + end_color)
    return res


def parse_reply(reply: str):
    global MAX_LEN, truncate, bracket_prob, parse_flag
    if parse_flag:
        # 去掉头尾的标点符号
        reply = reply.strip('”“’‘\"\'!！。.?？~')
        res = re.split('，|。', reply)
    else:
        res = [reply]

    if len(res) > 2:
        print(f'Truncate probability: {truncate}')
        for i in range(len(truncate)):  # 让ai少说点
            try:
                if random.random() < truncate[i]:
                    res.pop()
                    print('truncate!')
            except: continue

    try:
        if random.random() < bracket_prob[0]:  # 老互联网冲浪人士了（）
            res[-1] += '喵~'
        elif random.random() < bracket_prob[1]:
            res[-1] += '~'
    except: pass

    if len(res) > MAX_LEN:  # 有时候bot说太多了
        res = res[:MAX_LEN]

    print(f'处理后回复: {res}')
    return res


def load_parse_config(path=None):
    global api_key, proxy, bot_qq, bot_nickname, api_endpoint
    with open('configs/bot_config.json' if path is None else 'configs/'+path, 'r', encoding='utf-8') as f:
        configs = json.load(f)
        bot_nickname = configs['fixed_params']['bot_nickname']
        bot_qq = configs['fixed_params']['bot_qq']
        api_key = configs['fixed_params']['api-key']
        api_endpoint = configs['fixed_params']['api_endpoint']
        proxy = configs['fixed_params']['proxy']
        parse_config = configs['parse_config']
        for config in parse_config.keys():
            globals()[config] = parse_config[config]


if __name__ == '__main__':
    load_parse_config()
    print(parse_reply('我感觉你喜欢云宝吗？她可是很酷的小马。'))
    # print(parse_recieved_msg('”好啊，我这就来。“'))
