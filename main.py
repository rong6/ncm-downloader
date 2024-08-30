import os
import json
import requests
from tqdm import tqdm
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, USLT

GREEN = "\033[32m"
RESET = "\033[0m"
lines = [
    "  _   _  ____ __  __    ____   _____        ___   _ _     ___    _    ____  _____ ____  ",
    " | \\ | |/ ___|  \\/  |  |  _ \\ / _ \\ \\      / / \\ | | |   / _ \\  / \\  |  _ \\| ____|  _ \\ ",
    " |  \\| | |   | |\\/| |  | | | | | | \\ \\ /\\ / /|  \\| | |  | | | |/ _ \\ | | | |  _| | |_) |",
    " | |\\  | |___| |  | |  | |_| | |_| |\\ V  V / | |\\  | |__| |_| / ___ \\| |_| | |___|  _ < ",
    " |_| \\_|\\____|_|  |_|  |____/ \\___/  \\_/\\_/  |_| \\_|_____\\___/_/   \\_\\____/|_____|_| \\_\\"
]

for line in lines:
    print(f"{GREEN}{line}{RESET}")

# 读取配置文件
config_file = 'config.json'
if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {}

# 获取NCMAPI
if 'ncmapi' not in config or not config['ncmapi']:
    ncmapi = input("请输入NCMAPI URL：")
    config['ncmapi'] = ncmapi
elif not 'ncmapi':
    print("NCMAPI URL 不能为空。")
else:
    ncmapi = config['ncmapi']

# 获取cookie
if 'cookie' not in config:
    cookie = input("请输入cookie：")
    config['cookie'] = cookie
else:
    cookie = config['cookie']

# 保存配置文件
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=4)

# 选择下载类型
choice = input("请选择下载类型：[1]歌曲 [2]歌单 [3]专辑")

if choice == '1':
    song_id = input("请输入歌曲ID：")
    download_type = 'song'
elif choice == '2':
    playlist_id = input("请输入歌单ID：")
    download_type = 'playlist'
elif choice == '3':
    album_id = input("请输入专辑ID：")
    download_type = 'album'
else:
    print("输入错误，退出程序。")
    exit()

# 选择下载音质
print("请选择下载音质：")
qualities = {
    '1': 'standard => 标准',
    '2': 'higher => 较高',
    '3': 'exhigh => 极高',
    '4': 'lossless => 无损',
    '5': 'hires => Hi-Res',
    '6': 'jyeffect => 高清环绕声',
    '7': 'sky => 沉浸环绕声',
    '8': 'jymaster => 超清母带'
}
quality_levels = {
    '1': 'standard',
    '2': 'higher',
    '3': 'exhigh',
    '4': 'lossless',
    '5': 'hires',
    '6': 'jyeffect',
    '7': 'sky',
    '8': 'jymaster'
}
for k, v in qualities.items():
    print(f"[{k}] {v}")
quality_choice = input("输入对应数字：")
quality = quality_levels.get(quality_choice, 'standard')

# 处理歌词选项
lyric_option = input("请选择歌词处理方式：[1]下载歌词文件 [2]不下载歌词文件")


# 设置请求头
headers = {
    "cookie": config['cookie']
}

# 下载函数
def download_song(song_id, quality, lyric_option):
    retries = 3
    for _ in range(retries):
        try:
            # 请求歌曲详情
            song_detail_url = f"{ncmapi}/song/detail?ids={song_id}"
            song_detail_res = requests.get(song_detail_url, headers=headers, timeout=10).json()
            song_info = song_detail_res['songs'][0]
            song_name = song_info['name']
            artist_name = song_info['ar'][0]['name']
            album_name = song_info['al']['name']
            album_pic_url = song_info['al']['picUrl']

            # 请求下载链接
            download_url = f"{ncmapi}/song/url/v1?id={song_id}&level={quality}"
            download_res = requests.get(download_url, headers=headers, timeout=10).json()
            song_url = download_res['data'][0]['url']

            # 请求歌词
            lyric_url = f"{ncmapi}/lyric/new?id={song_id}"
            lyric_res = requests.get(lyric_url, headers=headers, timeout=10).json()
            lyrics = lyric_res['lrc']['lyric']

            # 下载歌曲
            song_filename = f"{album_name} - {song_name} - {artist_name}.mp3"
            print(f"正在下载：{song_filename}")
            with requests.get(song_url, stream=True, timeout=10) as r:
                r.raise_for_status()
                with open(song_filename, 'wb') as f:
                    total_size = int(r.headers.get('content-length', 0))
                    for chunk in tqdm(r.iter_content(chunk_size=8192), total=total_size//8192, unit='KB'):
                        f.write(chunk)

            # 处理歌词
            if lyric_option == '1':
                with open(song_filename.replace('.mp3', '.lrc'), 'w', encoding='utf-8') as f:
                    f.write(lyrics)
                audio = MP3(song_filename, ID3=ID3)
                audio.tags.add(USLT(encoding=3, text=lyrics))
                audio.save()
            elif lyric_option == '2':
                audio = MP3(song_filename, ID3=ID3)
                audio.tags.add(USLT(encoding=3, text=lyrics))
                audio.save()

            # 注入元数据
            audio = EasyID3(song_filename)
            audio['title'] = song_name
            audio['artist'] = artist_name
            audio['album'] = album_name
            audio.save()

            # 注入封面
            audio = MP3(song_filename, ID3=ID3)
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=requests.get(album_pic_url).content
                )
            )
            audio.save()
            break 

        except requests.exceptions.RequestException as e:
            print(f"请求失败，重试中... ({e})")
    else:
        print("多次重试后仍然失败，跳过该歌曲。")

# 根据选择下载歌曲、歌单或专辑
if download_type == 'song':
    download_song(song_id, quality, lyric_option)
elif download_type == 'playlist':
    playlist_url = f"{ncmapi}/playlist/track/all?id={playlist_id}"
    playlist_res = requests.get(playlist_url, headers=headers).json()
    song_ids = [str(song['id']) for song in playlist_res['songs']]
    for sid in song_ids:
        download_song(sid, quality, lyric_option)
elif download_type == 'album':
    album_url = f"{ncmapi}/album?id={album_id}"
    album_res = requests.get(album_url, headers=headers).json()
    song_ids = [str(song['id']) for song in album_res['songs']]
    for sid in song_ids:
        download_song(sid, quality, lyric_option)

input("下载完成！")
