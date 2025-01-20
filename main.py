import os
import json
import requests
from tqdm import tqdm
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, USLT
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from concurrent.futures import ThreadPoolExecutor, as_completed

RED = "\033[31m"
YELLOW = "\033[33m"
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

print("欢迎使用NCM Downloader！")
print("GitHub：https://github.com/rong6/ncm-downloader")

# 加载配置
def load_config():
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def get_input(prompt, key, config):
    if key not in config or not config[key]:
        value = input(prompt)
        config[key] = value
    return config[key]

config = load_config()
ncmapi = get_input("请输入NCMAPI URL：", 'ncmapi', config)
cookie = get_input("请输入cookie：", 'cookie', config)
save_config(config)

headers = {"cookie": cookie}

# 选择下载类型
def choose_download_type():
    while True:
        print(f"下载类型：{GREEN}[1]{RESET}歌曲 {GREEN}[2]{RESET}歌单 {GREEN}[3]{RESET}专辑 {GREEN}[4]{RESET}歌手所有歌曲")
        choice = input("请选择下载类型：")
        if choice == '1':
            return 'song', input("请输入歌曲ID：")
        elif choice == '2':
            return 'playlist', input("请输入歌单ID：")
        elif choice == '3':
            return 'album', input("请输入专辑ID：")
        elif choice == '4':
            return 'artist', input("请输入歌手ID：")
        else:
            print("输入错误，请重新输入。")

# 选择音质
def choose_quality():
    qualities = {
        '1': f'{GREEN}[1]{RESET} standard => 标准',
        '2': f'{GREEN}[2]{RESET} higher => 较高',
        '3': f'{GREEN}[3]{RESET} exhigh => 极高',
        '4': f'{GREEN}[4]{RESET} lossless => 无损',
        '5': f'{GREEN}[5]{RESET} hires => Hi-Res',
        '6': f'{GREEN}[6]{RESET} jyeffect => 高清环绕声',
        '7': f'{GREEN}[7]{RESET} sky => 沉浸环绕声',
        '8': f'{GREEN}[8]{RESET} jymaster => 超清母带'
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
        print(v)
    quality_choice = input("输入音质对应数字：")
    return quality_levels.get(quality_choice, 'standard')

# 选择歌词处理方式
def choose_lyric_option():
    print(f"歌词处理方式：{GREEN}[1]{RESET}下载歌词文件 {GREEN}[2]{RESET}不下载歌词文件")
    return input("请选择歌词处理方式：")

# 选择并发下载数量
def choose_concurrent_downloads():
    while True:
        try:
            num = int(input("请输入同时并发下载歌曲数（1-50）："))
            if 1 <= num <= 50:
                return num
            else:
                print("请输入1到50之间的数字。")
        except ValueError:
            print(f"{RED}Error{RESET}: 请输入有效的数字。")

# 注入元数据
def inject_metadata(audio_path, song_info, lyrics, cover_data):
    ext = os.path.splitext(audio_path)[-1].lower()
    if ext == '.mp3':
        audio = MP3(audio_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text=song_info['name']))
        audio.tags.add(TPE1(encoding=3, text=song_info['ar'][0]['name']))
        audio.tags.add(TALB(encoding=3, text=song_info['al']['name']))
        audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
        audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))
        audio.save()
    elif ext == '.flac':
        audio = FLAC(audio_path)
        audio['title'] = song_info['name']
        audio['artist'] = song_info['ar'][0]['name']
        audio['album'] = song_info['al']['name']
        audio['lyrics'] = lyrics
        picture = Picture()
        picture.data = cover_data
        picture.type = 3
        picture.mime = 'image/jpeg'
        audio.add_picture(picture)
        audio.save()

# 下载单首歌曲
def download_song(song_id, quality, folder_name, lyric_option):
    retries = 3
    for attempt in range(retries):
        try:
            # 获取歌曲详情
            song_detail_url = f"{ncmapi}/song/detail?ids={song_id}"
            song_detail_res = requests.get(song_detail_url, headers=headers, timeout=10).json()
            if 'songs' not in song_detail_res:
                raise KeyError("API响应中缺少'songs'字段")
            song_info = song_detail_res['songs'][0]
            song_name = song_info['name']
            artist_name = song_info['ar'][0]['name']
            album_name = song_info['al']['name']
            album_pic_url = song_info['al']['picUrl']

            # 获取下载链接
            download_url = f"{ncmapi}/song/url/v1?id={song_id}&level={quality}"
            download_res = requests.get(download_url, headers=headers, timeout=10).json()
            if 'data' not in download_res or not download_res['data']:
                raise KeyError("API响应中缺少'data'字段或数据为空")
            song_data = download_res['data'][0]
            song_url = song_data['url']
            type = song_data.get('type', 'mp3')

            if not song_url:
                print(f"{RED}Error{RESET}: 无法获取歌曲 {song_name} 的下载链接，可能是版权限制。")
                with open('fail.log', 'a') as f:
                    f.write(f"{song_id} - {song_name}: 无法获取下载链接，可能是版权限制。\n")
                return False

            # 获取歌词
            lyric_url = f"{ncmapi}/lyric/new?id={song_id}"
            lyric_res = requests.get(lyric_url, headers=headers, timeout=10).json()
            lyrics = lyric_res.get('lrc', {}).get('lyric', '')

            # 设置文件扩展名
            ext = f".{type.lower()}"
            if ext not in ['.mp3', '.flac']:
                ext = '.mp3'  # 默认使用mp3

            # 下载歌曲
            song_filename = os.path.join(folder_name, f"{album_name} - {song_name} - {artist_name}{ext}")
            print(f"{YELLOW}正在下载{RESET}：{song_filename}")
            with requests.get(song_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(song_filename, 'wb') as f, tqdm(
                    desc=f"{song_name} - {artist_name}",
                    total=total_size,
                    unit='MB',
                    unit_scale=True,
                    unit_divisor=1024 * 1024,
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size / (1024 * 1024))

            # 确保文件下载完成后再进行元数据注入
            if os.path.getsize(song_filename) == total_size:
                # 注入元数据
                cover_data = requests.get(album_pic_url).content
                inject_metadata(song_filename, song_info, lyrics, cover_data)

                # 用户选择下载歌词文件处理
                if lyric_option == '1':
                    lyric_filename = os.path.join(folder_name, f"{album_name} - {song_name} - {artist_name}.lrc")
                    with open(lyric_filename, 'w', encoding='utf-8') as f:
                        f.write(lyrics)
                    print(f"{GREEN}歌词已保存{RESET}：{lyric_filename}")

                print(f"{GREEN}下载完成{RESET}：{song_filename}")
                return True
            else:
                raise Exception("文件大小不匹配，下载可能不完整。")

        except requests.exceptions.RequestException as e:
            print(f"{RED}请求失败，重试中... ({e}){RESET}")
        except Exception as e:
            print(f"{RED}处理失败{RESET}：{e}")
            with open('fail.log', 'a') as f:
                f.write(f"{song_id}: {e}\n")
    else:
        print(f"{YELLOW}多次重试后仍然失败，跳过该歌曲。{RESET}")
        with open('fail.log', 'a') as f:
            f.write(f"{song_id} - {song_name}: 下载失败\n")
        return False

# 批量下载歌曲
def download_all(song_ids, folder_name, quality, lyric_option, max_workers):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_song, sid, quality, folder_name, lyric_option): sid for sid in song_ids}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"{RED}下载失败{RESET}：{e}")

# 主程序
download_type, id_value = choose_download_type()
quality = choose_quality()
lyric_option = choose_lyric_option()
max_workers = choose_concurrent_downloads()

if download_type == 'artist':
    artist_albums_url = f"{ncmapi}/artist/album?id={id_value}"
    artist_albums_res = requests.get(artist_albums_url, headers=headers).json()
    if 'hotAlbums' not in artist_albums_res:
        raise KeyError("API响应中缺少'hotAlbums'字段")
    albums = artist_albums_res['hotAlbums']

    for album in albums:
        album_name = album['name']
        folder_name = f"{album['artist']['name']} - {album_name}"
        os.makedirs(folder_name, exist_ok=True)
        print(f"正在下载专辑：{album_name}")

        album_tracks_url = f"{ncmapi}/album?id={album['id']}"
        album_tracks_res = requests.get(album_tracks_url, headers=headers).json()
        if 'songs' not in album_tracks_res:
            raise KeyError("API响应中缺少'songs'字段")
        song_ids = [str(track['id']) for track in album_tracks_res['songs']]
        download_all(song_ids, folder_name, quality, lyric_option, max_workers)

elif download_type == 'song':
    download_song(id_value, quality, "", lyric_option)
elif download_type == 'playlist':
    playlist_url = f"{ncmapi}/playlist/track/all?id={id_value}"
    playlist_res = requests.get(playlist_url, headers=headers).json()
    if 'songs' not in playlist_res:
        raise KeyError("API响应中缺少'songs'字段")
    song_ids = [str(song['id']) for song in playlist_res['songs']]
    folder_name = f"Playlist - {id_value}"
    os.makedirs(folder_name, exist_ok=True)
    download_all(song_ids, folder_name, quality, lyric_option, max_workers)
elif download_type == 'album':
    album_tracks_url = f"{ncmapi}/album?id={id_value}"
    album_tracks_res = requests.get(album_tracks_url, headers=headers).json()
    if 'songs' not in album_tracks_res:
        raise KeyError("API响应中缺少'songs'字段")
    song_ids = [str(track['id']) for track in album_tracks_res['songs']]
    album_name = album_tracks_res['album']['name']
    folder_name = f"专辑 - {album_name}"
    os.makedirs(folder_name, exist_ok=True)
    download_all(song_ids, folder_name, quality, lyric_option, max_workers)

print(f"{GREEN}下载完成！请检查文件夹。{RESET}")
print("下载失败的歌曲请查看fail.log文件。")