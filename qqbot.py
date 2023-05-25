"""
by LUMO_Xu uid: 66970100

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from pycqBot.cqApi import cqHttpApi, cqLog
from pycqBot import Message, cqCode
import pandas as pd
import random
import logging
import chat
import time
import json
from datetime import datetime
import re
import os

red_color = '\033[0;31m'
blue_color = '\033[0;34m'
cyan_color = '\033[0;36m'
end_color = '\033[0m'

cqLog(logging.INFO)

prompt = None
unreplied_msg = 0
history_flag = False
global_chat_record = []


def check_chatrec():
    global global_chat_record, MAX_CACHED_RECORDS, MAX_CACHED_TIME, unreplied_msg
    global_chat_record = sorted(global_chat_record, key=lambda x: x[2])
    now = time.time()
    if global_chat_record:
        while now - global_chat_record[0][2] > MAX_CACHED_TIME:  # 删除已经过时的消息
            del global_chat_record[0]
            if unreplied_msg > 0:
                unreplied_msg -= 1
            if not global_chat_record:
                return
        while len(global_chat_record) > MAX_CACHED_RECORDS:  # 消息寄存器最多存?条消息（默认16）
            del global_chat_record[0]


def update_global_chatrec(message: Message):
    global global_chat_record
    global_chat_record.append((message.sender['user_id'], message.text, message.time, get_nickname(message)))
    check_chatrec()


def update_global_chatrec_bot(message: tuple):
    global global_chat_record
    global_chat_record.append(message)
    check_chatrec()


def print_global_chatrec():
    global unreplied_msg, REPLY_FREQ, MAX_CACHED_RECORDS
    print(red_color + f'======存档聊天记录（最多{MAX_CACHED_RECORDS}条）======' + end_color)
    global global_chat_record
    for rec in global_chat_record:
        print(f'发送者: {rec[3]}({rec[0]})  内容:{rec[1]}  时间: {rec[2]}')
    print(f'积攒消息数: {unreplied_msg}/为{REPLY_FREQ}时回复')
    print(red_color + '===================================' + end_color)


def update_msgs_counter(group_id, num_of_msgs, api_used=1):
    if group_id in id_name.keys():
        group_name = id_name[group_id]
    else:
        group_name = 'unknown'
    day_now = datetime.fromtimestamp(time.time()).day
    counter = pd.read_csv('msgs_counter.csv')
    if 'group_id' in counter.columns.values:
        counter = counter.set_index('group_id')
    if list(counter.index):
        day_then = int(counter.loc[list(counter.index)[0]]['day'])
    else:
        day_then = day_now

    if day_then != day_now:  # new day, clear the counter.
        for group in list(counter.index):
            counter.loc[group] = [0, 0, day_now]
    # now, update.
    if group_id not in list(counter.index):
        counter.loc[group_id] = [api_used, num_of_msgs, day_now]
    else:
        counter.loc[group_id]['api_used'] += api_used
        counter.loc[group_id]['msgs_sent'] += num_of_msgs
        api_used_times = counter.loc[group_id]['api_used']
        msgs_sent = counter.loc[group_id]['msgs_sent']
        if api_used_times % 5 == 0 and api_used:  # notice the admin
            reply = f'Group {group_id}({group_name}): ' \
                    f'Bot has successfully used gpt-api for {api_used_times} times.\n' \
                    f'{msgs_sent} messages have been sent.'
            print(reply)
            cqapi.send_private_msg(user_id=admin_qq[0], message=reply, auto_escape=True)
    counter.to_csv('msgs_counter.csv')


def get_type_time(string):
    """
    打字时间模拟
    """
    global tpc
    return 1.5 + tpc*len(string)


def if_suspected():
    global bot_qq
    sus = chat.suspected
    for rec in global_chat_record:
        for s in sus:
            if s in rec[1] and rec[0] not in [-1, bot_qq]:
                return True
    return False


def parse_recieved_msg(message: Message or dict, sender):
    global bot_nickname, current_group_id
    if isinstance(message, dict):
        string = message['raw_message']
    else:
        string = message.text
    if string.startswith('[CQ:json'):
        if 'QQ小程序' in string and '哔哩哔哩' in string:
            try:
                name_idx = string.find('data=') + 5
                end_idx = len(string)
                string = string[name_idx: end_idx-1]
                bili_json = json.loads(string.replace('&#44', "").replace(";", ","))
                vid_name = bili_json['meta']['detail_1']['desc']
                print('name:', vid_name)
                return f'转发视频: {vid_name}', False, False
            except ValueError:
                print('视频解析错误')
                pass
        return None, False, True
    query = re.findall("\[.*?\]", string, re.I | re.M)
    at_flag = sender if f'[CQ:at,qq={bot_qq}]' in query else ''
    img_flag = False
    ocr_text = None
    for i in query:
        if i == f'[CQ:at,qq={bot_qq}]':
            string = string.replace(i, f' {bot_nickname} ')
        if i.startswith('[CQ:image,file') and not img_flag and not isinstance(message, dict):
            img_flag = True
            j = 0
            for j in range(len(message.code)):
                if message.code[j]['type'] == 'image':
                    break
            img_id = message.code[j]['data']['file']  # 若有图片，找到消息第一张图片的img_id，其他丢弃不分析
            res = cqapi.add_task(_ocr(img_id))
            ocr_text = open('ocr.txt', 'r', encoding='utf-8').read().strip()
            if ocr_text is not False and len(ocr_text) > 20:  # 杂乱信息，gpt先总结一下
                ocr_text = '（一张图片）内容: ' + chat.describe_image(ocr_text)
            empty = ''
            string = string.replace(i, f' {ocr_text if ocr_text != False else empty} ')
        else:
            string = string.replace(i, ' ')
    string = string.strip()
    empty_flag = True if not string else False
    return string, at_flag, empty_flag


def send_sticker(message: Message):
    if not os.path.exists('stickers.json'):
        raise FileNotFoundError('stickers.json not found.')
    with open('stickers.json', 'r') as f:
        stickers = json.load(f)
        allowed = stickers['allowed']
        stickers_dict = stickers['stickers']
    pick = random.sample(allowed, 1)[0]
    url = stickers_dict[str(pick)]
    try:
        time.sleep(1.5 + random.random())
        img = cqCode.image(pick, url)
        if message is not None:
            message.reply_not_code(img)
            update_msgs_counter(message.group_id, 1, 0)
        else:
            cqapi.send_group_msg(message=img, group_id=current_group_id)
            update_msgs_counter(current_group_id, 1, 0)
        print(f'Replied sticker: {pick}')
    except:
        print(f'Failed to reply sticker: {pick}')


def reply_msg(message: Message or None, sender):
    global unreplied_msg, global_chat_record, prompt, nickname_mode, current_group_id, reply_flag, STICKER_PROB
    unreplied_msg = 0
    temp_chat_record = chat.get_prompt(global_chat_record, nickname_mode)
    print(cyan_color + '=' * 22 + '待填聊天记录' + '=' * 22 + '\n' + temp_chat_record + '\n' + '=' * 50 + end_color)
    time_question = time.time()
    try:
        replies = chat.parse_reply(chat.answer(temp_chat_record, prompt))  # may stuck at this step.
        if replies and reply_flag:
            replies[0] = sender + ', ' + replies[0]
    except:
        print('Internet issues! Will not answer this time.')
        if random.random() < STICKER_PROB:
            send_sticker(message)
        return
    if not replies:  # 列表为空
        if random.random() < STICKER_PROB:
            send_sticker(message)
        return
    elif len(replies) == 1 and not replies[0]:  # 回复为空
        if random.random() < STICKER_PROB:
            send_sticker(message)
        return
    update_msgs_counter(current_group_id, len(replies))

    times = [get_type_time(reply) for reply in replies]
    time_get_answer = time.time()
    if time_get_answer - time_question > times[0] + 1:  # 等的过久，直接回复第一条
        time.sleep(2)
        if message is None:
            cqapi.send_group_msg(group_id=current_group_id, message=replies[0], auto_escape=True)
        else:
            message.reply_not_code(replies[0])
        update_global_chatrec_bot((-1, replies[0], time_get_answer, '你'))
    else:  # 等”打好字“再回复第一条与更新
        time.sleep(times[0] + 1 - (time_get_answer - time_question))
        if message is None:
            cqapi.send_group_msg(group_id=current_group_id, message=replies[0], auto_escape=True)
        else:
            message.reply_not_code(replies[0])
        update_global_chatrec_bot((-1, replies[0], time.time(), '你'))
    for i in range(1, len(replies)):
        time.sleep(times[i])
        if message is None:
            cqapi.send_group_msg(group_id=current_group_id, message=replies[i], auto_escape=True)
        else:
            message.reply_not_code(replies[i])
        update_global_chatrec_bot((-1, replies[i], time.time(), '你'))

    if random.random() < STICKER_PROB:
        time.sleep(3)
        send_sticker(message)


async def _on_group_msg(message: Message):
    global global_chat_record, current_group_id, bot_nickname
    global_chat_record = []
    data = {
        'group_id': current_group_id
    }
    data = await cqapi._asynclink("/get_group_msg_history", data=data)
    for msg in data['data']['messages']:
        parsed_msg, at_flag, empty_flag = parse_recieved_msg(msg, '')
        # print(parsed_msg, at_flag, empty_flag)
        if empty_flag:
            continue
        if msg['sender']['card']:
            nickname = msg['sender']['card']
        else:
            nickname = msg['sender']['nickname']
        if nickname == bot_nickname:
            nickname = '你'
        update_global_chatrec_bot((msg['sender']['user_id'], parsed_msg, msg['time'], nickname))
    check_chatrec()


def get_nickname(message: Message):
    global bot_nickname
    if message.sender['card']:
        return message.sender['card'] if message.sender['card'] != bot_nickname else '你'
    else:
        return message.sender['nickname'] if message.sender['nickname'] != bot_nickname else '你'


def on_group_msg(message: Message):
    global unreplied_msg, global_chat_record, history_flag, current_group_id, prompt, REPLY_FREQ, show_other_groups
    if message.group_id != current_group_id:  # 把不想要的群的消息直接扔掉！
        if show_other_groups:
            print('[Msg from other groups:', message.text if len(message.text) <= 80 else
                  red_color + '*tl,dr*' + end_color, 'from:',
                  id_name[message.group_id] + f'({id_idx[message.group_id]})', ']')
        return
    if not history_flag:
        print('首次启动，获取历史信息中...')
        cqapi.add_task(_on_group_msg(message))
    try:
        print(F"新消息: {message.text if len(message.text) < 100 else red_color + '*tl,dr*' + end_color}  "
              F"(发送者: {get_nickname(message)}({message.sender['user_id']}), 发送时间: {message.time})")
    except Exception as e:
        print('???')
        return
    parsed_msg, at_flag, empty_flag = parse_recieved_msg(message, get_nickname(message))
    if empty_flag:
        return 0
    message.text = parsed_msg
    update_global_chatrec(message)
    if not history_flag:
        time.sleep(4)
    try:
        if global_chat_record[:-2][2] == global_chat_record[-1][2]:
            global_chat_record.pop()
    except Exception as e:
        pass
    if not history_flag:
        # print_global_chatrec()
        unreplied_msg = len(global_chat_record) - 1
        print(unreplied_msg)
    history_flag = True
    unreplied_msg += 1
    print_global_chatrec()
    # 有人怀疑bot，赶紧关掉。
    if if_suspected():
        time.sleep(2)
        cqapi.send_group_msg(current_group_id, '6')
        cqapi.send_private_msg(admin_qq[0], 'Emergency: Bot may be suspected! Automatically shutting down...')
        switch_group(0)
        return
    if unreplied_msg >= REPLY_FREQ or at_flag:
        reply_msg(message, at_flag)


def switch_group(idx, message=None):
    global current_group_id, unreplied_msg, history_flag, global_chat_record
    current_group_id = bot_group_id[idx]
    if message is not None:
        message.reply_not_code('Bot has been switched to' + str(bot_group_info[idx]))
    else:
        cqapi.send_private_msg(admin_qq[0], 'Bot has been switched to' + str(bot_group_info[idx]))
    # initialize
    unreplied_msg = 0
    history_flag = False
    global_chat_record = []


def load_bot_config(path=None):
    global bot_group_info, bot_group_id, id_name, id_idx, idx_id, bot_qq, admin_qq, bot_nickname
    with open('configs/bot_config.json' if path is None else 'configs/'+path, 'r', encoding='utf-8') as f:
        configs = json.load(f)
        bot_config = configs['bot_config']
        bot_nickname = configs['fixed_params']['bot_nickname']
        bot_qq = configs['fixed_params']['bot_qq']
        admin_qq = configs['fixed_params']['admin_qq']
        for config in bot_config.keys():
            globals()[config] = bot_config[config]
    bot_group_id = [group[0] for group in bot_group_info]
    id_name = {gid: name for gid, name in bot_group_info}
    id_idx = {bot_group_info[idx][0]: idx for idx in range(len(bot_group_info))}
    idx_id = {idx: gid for gid, idx in id_idx.items()}


def interpret_image(data):
    global ocr_confidence
    res = []
    if data['data'] is None:
        return False
    for text_info in data['data']['texts']:
        if text_info['confidence'] > ocr_confidence:
            res.append(text_info['text'])
    return ' '.join(res)


async def _ocr(img_id):
    print(f'开始识别图片: {img_id}')
    data = {
        'image': img_id
    }
    a = time.time()
    data = await cqapi._asynclink("/ocr_image", data=data)
    b = time.time()
    parsed = interpret_image(data)
    print('识别文字:', '无文字' if parsed is False else parsed, f' 识别用时: {int((b-a)*1000)/1000}s')
    with open('ocr.txt', 'w', encoding='utf-8') as f:
        f.write(parsed)
    return parsed


def admin(message: Message):
    global current_group_id, unreplied_msg, history_flag, global_chat_record, show_other_groups
    print('received cmd:', message.text)
    cmds = message.text.split(';')
    for cmd in cmds:
        cmd = cmd.strip()
        if 'help' in cmd:
            modes = ['show: 展示可用群及编号',
                     'switch [编号]: 切换bot至另一个群',
                     'curr: 显示目前bot群号',
                     'other [show/hide]: 展示/隐藏其他群的消息',
                     'load xxx.json: 加载bot预设',
                     'echo xxx: 调试功能，私聊bot，测试号是否被封']
            rep = '\n'.join(modes)
            message.reply_not_code(rep)
        if cmd == 'show':
            rep = '\n'.join(map(str, (enumerate(bot_group_info))))
            message.reply_not_code(rep)
        if 'switch' in cmd:
            try:
                switched = int(cmd.split()[1])
                switch_group(switched, message)
            except: pass
        if cmd == 'curr':
            message.reply_not_code('current:' + str(current_group_id))
        if cmd.startswith('other '):
            try:
                if cmd.split()[1] == 'show':
                    show_other_groups = True
                    message.reply_not_code('Msgs from other groups will be shown.')
                elif cmd.split()[1] == 'hide':
                    show_other_groups = False
                    message.reply_not_code('Msgs from other groups will be hidden.')
            except: pass
        if cmd.startswith('load '):
            try:
                path = cmd.split()[1]
                load_bot_config(path)
                chat.load_parse_config(path)
                unreplied_msg = 0
                history_flag = False
                global_chat_record = []
                message.reply_not_code(f'loaded config: {path}.')
            except:
                message.reply_not_code(f'Failed to load config.')

        if cmd.startswith('echo'):
            message.reply_not_code(cmd[5:])


load_bot_config()
chat.load_parse_config()

cqapi = cqHttpApi()

bot = cqapi.create_bot(
    group_id_list=bot_group_id,
    user_id_list=admin_qq  # admin,
)

bot.on_group_msg = on_group_msg
bot.on_private_msg = admin

print(f'当前进程pid: {os.getpid()}')

bot.start()
