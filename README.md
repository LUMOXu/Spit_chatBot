# Spit_chatBot
b站视频BV1gm4y1C7oY中，Spit使用的源代码。

go-cqhttp: https://github.com/Mrs4s/go-cqhttp

pycqbot: https://github.com/FengLiuFeseliud/pycqBot

***

# ChatBot 使用指南
## 一．程序运行原理
Bot 基于 pycqBot 包与 go-cqhttp 运行，其同一时刻只能在一个群内发消息。其被切换到一个群（switch 命令，后面会提）后，若第一次接收到群消息，则会获得群内的历史消息。

Bot 会将其筛选（去掉表情等等），经过处理后填入全局聊天记录中。之后每接收到一条处理后不为空的消息，bot 会更新全局聊天记录，全局变量 unreplied_msg 会加 1。

更新全局消息记录的方法，bot 先把已经超过一定时长(MAX_CACHED_TIME)的消息去掉，再加上新消息，去掉超过缓存容量(MAX_CACHED_RECORDS)的消息，并将消息按发的时间排序。每条消息的记录为[发送者：...消息：...时间：...]。之后打印出此时的全局消息记录。

如果消息内含图片，会用腾讯自己的 api 对第一张图片进行 ocr 识别，之后把图片转化为文字。（没找到并发任务返回值，因此用了笨方法，用一个 txt 存储输出 ocr 得到的内容）

若 unreplied_msg 等于全局参数 REPLY_FREQ，或者在之前处理收到的新消息时检测到了@bot，则 bot 会将全局消息记录转化为供 gpt 识读的格式。之后与人设一起传给 gpt，等待答复。unreplied_msg 归零。

得到 bot 的回复后，对回复进行后处理。其有以下功能：
1. 分段：正常人聊天，一句话基本会分好几次，因此以标点符号为界对消息分段
(parse_flag)。

2. 随机截断：有时候 bot 说的话太多（出现过 10 段的现象），因此可以随机截断
(truncate)，或者设定每次 bot 最多说几段话(MAX_LEN)。

3. 加括号：为了让 bot 说话更有网络冲浪的味道，bot 的最后一段话后有可能加括号。(bracket_prob)

chat.answer()函数得到了处理后的 bot 回复，是一个列表（会被打印出来），bot 会模拟打字速度，一条一条地发送，同时更新消息计数器 msgs_counter.csv。

如果所有消息都发完了或者无消息可发，有一定概率(STICKER_PROB)会随机从表情包库(sticker.json)里挑一张表情包发。如果今天已在群里发的消息是 5 的倍数，bot 会给主管理员发信息提醒。

Bot 每在群里发一条消息，也会同时更新全局消息记录，但 unreplied_msg 不会变。

接下来介绍管理员。管理员可有多个，其中有一个主管理员，他能接收到 bot 的大部分提示消息（哪些忘了，懒得看），副管理员只能接收到小部分。主副管理员均可通过私聊向bot 发送命令，让 bot 切换群聊/加载配置（在命令一节会讲到）。

## 二．配置参数详解
可以通过 load 命令（后面提）加载 config 文件夹里的 json 配置文件来自定义你的 bot。

Bot 启动时默认加载的是聊天模式即 bot_config.json，接下来以其为例介绍其中的每个参数。

```
# =======bot_config.json============ #
{
"fixed_params" : # 想要改变里面的参数，需要重启应用/重启 go-cqhttp，直接 load 没用
{
"bot_qq" : 114514 , # bot 的 qq
"bot_nickname" : "SpitFlight", # bot 的昵称，处理消息会用到。
"admin_qq" : [], # 一个列表，里面是管理员们的 qq，第一个是主管理，之后是副管理。
"api-key" : "", # 字符串，你 openai 的 apikey，有 chatgpt 账号的就能容易搞到，具体百
度。
"proxy" : "http://xxx.xxx.xxx.xxx:xxxx" #你的 vpn 的代理服务器地址，否则访问不了
openai。开 vpn 后查你的电脑的“网络与 Internet 设置-代理”就可找到。
},
"bot_config" : # qqbot.py 里用的一些参数，可 load 改变
{
"bot_group_info" : # bot 可切换到的群列表
[[1, "关闭"],
[62****485, "测试群"], # 格式如左
[14****540, "粉丝群"]], # 每个群的编号从上到下分别是 0, 1, 2, ...
"current_group_id" : 62****485, # 启动 bot 后默认在的群
"tpc" : 0.65, # 输出每个字需要多少秒
"MAX_CACHED_RECORDS" : 16, # 最大缓存消息数
"MAX_CACHED_TIME" : 3600, # 缓存消息允许的最长历史(s)
"REPLY_FREQ" : 5, # 几条消息回一次
"STICKER_PROB" : 0.65, # 发表情包概率
"ocr_confidence" : 85, # ocr 得到的结果置信度多大，才算做图片文字
"show_other_groups" : true, # 是否在后台输出其他群的消息
"nickname_mode" : true, # 送给 gpt 聊天记录时，是用 ABC 代替群友名字还是直接用昵称
"reply_flag": true, # gpt 输出后，是否在输出消息的最前端加上 at bot 人的名字
"prompt" : null # 人设，若为 null 即为 prompt.txt 的内容
},
"parse_config" : # chat.py 里用的一些参数，可 load 改变
{
"truncate" : [0.1, 0.1], # 截断消息的概率。分句得到消息列表后，会按列表中的概率进行pop()操作，次数等于列表长度。
"MAX_LEN" : 12, # 分句得到的消息列表，最多保留前几段消息。
"suspected": [], # 聊天记录里出现这些词后，bot 会认为自己被怀疑，单走一个 6 后 switch
0（作用后面会讲）
"bracket_prob" : [0.5, 0.4], # 加括号的概率，印象中第一个对应加（），第二个对应（
"parse_flag" : true # 是否进行分句
}
}
```

可以对比助手模式的 assistant_config.json 看看两个配置的差别。可以发现助手模式 REPLY_FREQ 很大（只有 at 才会召唤），tpc 更小，不会对消息分段。你也可以写自己的 config。

## 三．管理员命令大全

管理员可通过私聊向 bot 发送命令，让 bot 切换群聊/加载配置等。**注意，命令都是小写字母。且可以用分号;分隔的方式依次执行命令。
有时候 bot 不会回复内容，可能是腾讯搞的鬼，不过这个时候命令也执行了，且 bot 在群中还可以发消息。**

1. show
Bot 会回复当前的可用群与编号。

2. switch
格式：switch [群编号]，注意不是群号。Bot 会切换到编号群，同时清空 global_chatrec 等等。并给出反馈。switch 0 一般就是关闭 bot。（依照之前的bot_group_info，0 代表监听群号为 1 的群，这肯定监听不到什么东西）

3. curr
Bot 会回复当前所在（严格地说，所监听）的群信息。

4. other show/hide
改变 show_other_groups，显示/隐藏其他群的消息。

5. load
格式：load [xxx.json]。加载 config/xxx.json 为 bot 配置，会改变 qqbot.py 与 chat.py 中全局变量的值。

6. echo
格式：echo [xxx]。调试功能，bot 会回复你 xxx，检测 bot 开没开/有没有被封号。

## 四．配置教程

（以下步骤需要 vpn，如果你有境外服务器/肉身在境外，把程序内所有关于 PROXY 的东西
删掉）

1. 打开 config.yml，输入你的 bot qq 与密码（关于扫码登陆的事项见后）。

2. 下载 go-cqhttp.exe (https://github.com/Mrs4s/go-cqhttp/releases)，并把它放到 bot 的文件夹里。在命令行运行 go-cqhttp.exe，理想情况下，会直接跳到成功登录，类似下图：
[![p9cFEB6.png](https://s1.ax1x.com/2023/05/13/p9cFEB6.png)](https://imgse.com/i/p9cFEB6)
同时会生成一个 device.json 与 session.token 文件，只要有 session.token，之后启动 go-cqhttp 或者 pycqBot 包调用 go-cqhttp 就不用再登陆了，否则还要登录。
如果登不上，把 session 删掉，device.json 的 protocol 改成 3 试试，如果 protocol 是 3，可以使用扫码登陆，为 6 就不可以。（遇到其他问题请自行百度或者在 issues 询问）
如果 device.json 的 protocol 是默认的 6，相当于你在一台虚拟的 ipad 上登了 qq，如果你在ipad 上登 qq 就会把这个 qq 踢下线。若为 3 则为 MacOS。

3. 登陆成功之后，关掉窗口即可。

4. 确保你用的是 python 3.9（其他版本没试过，应该问题不大），安装 requirements。只用装三个包：pandas, pycqbot, openai。

5. 编辑 prompt.txt 里默认的人设（可选）

6. 把 config/里面的配置文件的 api_key, bot_qq, admin_qq, bot_group_info 等等填完整。

7. 运行 qqbot.py 即可。如果你第三步成功了但这步没有登录上，请到 github 的 pycqbot 或者 go-cqhttp 的 issues 下面反映问题。（可能是 config.yml 的配置问题，不过笔者也不懂这块，在自己的电脑上能跑就行）

8. 如果你想编辑表情包，把 sticker.json 中的 sticker 中的 url 改成图片的 url 即可。allowed里是可以发出来的表情包编号。注意表情包是随机选取的。

## 五．注意事项
1. MAX_CACHED_RECORDS 应该尽量大一些，以增进 bot 对群聊历史消息的了解。

2. gpt-3.5 的官方价格是 0.002 美金/1k token，也就是 5 美金（目前新用户的免费额度）可以让 bot 输入/输出一共 2.5 Mtoken 的内容，大概 170 万字。如果你可以用 gpt-4 的 api，价格大概要贵 20-30 倍。

3. $\color{red}{祝各位与数字生命聊(tiao)天(xi)愉快，不要用这个 bot 做坏事，希望大家以后能对消息的来源多加甄别。}$

就写这么多。


>pdf LUMO_Xu 23/5/8

>初版markdown liu_zhou 23/5/13

