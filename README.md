# MiBoyDaily

利用小米人在传感器实现每日自动化

## Info

这个非常个人向，只是提供一个人在传感器的应用，你可以利用这个思路更改代码，需要有程序基础，如果想交流可以给我发邮件。

## 需要

1. 小米人在传感器
2. 小爱音箱 Pro 用来作为蓝牙 mesh
3. 你想用的任何小米能连接蓝牙的设备

## 安装

1. install pdm
2. pdm install
3. export GitHub Token -> 参考[巧妙利用 iOS 的快捷指令配合 GitHub Actions 实现自动化](https://github.com/yihong0618/gitblog/issues/198)来配置你的 Actions
4. 参考 [Miservice](https://github.com/yihong0618/MiService) 拿到人在传感器和小爱 Pro 的 did
5. 更改代码的 schedule 自行添加 task
6. pdm run miboy_daily.py -h

我的 tg [频道](https://t.me/hyi0618)每天自动的早起问候就是由该自动化发布的

![image](https://github.com/user-attachments/assets/14a10cae-2de9-4cf1-85e7-5f82cf5f171f)
