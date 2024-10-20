<div align="center">
<h1>NCM-DOWNLOADER</h1>
<img src="https://socialify.git.ci/rong6/ncm-downloader/image?description=1&font=Inter&name=1&owner=1&pattern=Circuit%20Board&theme=Dark" alt="Cover Image" width="650">
</div>

## 这是什么？
这是一个基于[NeteaseCloudMusicApi](https://gitlab.com/Binaryify/neteasecloudmusicapi)的网易云音乐歌曲、歌单、专辑下载工具，支持批量下载，支持对下载的音乐注入元数据（即文件属性包含歌曲名、专辑名、歌手名等信息）。

> [!WARNING]  
> 本项目仍在开发中，目前可能不稳定，请酌情使用！
> 2024.10.20：注入元数据功能暂时不可用。

## 使用

克隆源码并安装Python库。  

``` bash
git clone https://github.com/rong6/ncm-downloader.git
cd ncm-downloader
pip install -r requirements.txt
```

然后，你需要部署[NeteaseCloudMusicApi](https://gitlab.com/Binaryify/neteasecloudmusicapi)，可在本地也可在云端。   

打开`https://<YourNeteaseCloudMusicApiDomain>/qrlogin.html`，按下`F12`打开开发者工具，切换至`网络`选项卡，扫码登录网易云。  
找到`/check?key=xxx`的相关请求，切换至`预览`选项卡，查看`message`值为`授权登陆成功`或`code`值为`803`的那个请求，右键复制上面`cookie`的值。
![cookie_setting](https://go.xiaobai.mom/https://img.pub/p/6ec896b078da279bd0a9.png)。

运行：
``` bash
python main.py
```
输入你NeteaseCloudMusicApi的网址（带协议头，结尾不带`/`），再粘贴你上面获取到的Cookie，接下来按提示操作即可。**注意，若你的账号没有会员则无法下载会员歌曲，也无法下载会员音质，无法越权使用。**

## 预览图
![preview](https://go.xiaobai.mom/https://img.pub/p/ee3c12e719ec848de7d8.png)
## 免责声明
本程序仅供个人学习和交流使用，请勿将其用于任何商业目的或非法用途。使用本程序下载的内容应当符合相关法律法规和平台服务协议的要求。开发者不对因使用本程序而产生的任何直接或间接的法律责任负责。

请尊重版权，支持正版音乐。如果您喜欢某些音乐作品，请购买正版或通过合法渠道获取。任何因未经授权下载、传播或使用受版权保护的内容而引发的后果，均由使用者自行承担。

开发者对本程序的使用效果不作任何保证，不对因使用或无法使用本程序而导致的任何损失负责。使用本程序的风险由使用者自行承担。