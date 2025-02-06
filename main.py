import os
import json
import requests
import traceback
from datetime import datetime
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

# 处理歌词数据
def process_lyrics(lyrics):
    lines = lyrics.split('\n')
    processed_lyrics = []
    for line in lines:
        if line.startswith('{"t":'):
            json_line = json.loads(line)
            timestamp = json_line['t']
            text = ''.join([c['tx'] for c in json_line['c']])
            minutes = timestamp // 60000
            seconds = (timestamp % 60000) // 1000
            milliseconds = timestamp % 1000
            processed_lyrics.append(f"[{minutes:02}:{seconds:02}.{milliseconds:03}]{text}")
        else:
            processed_lyrics.append(line)
    return '\n'.join(processed_lyrics)

def log_error(error_type, message, details=None, song_info=None):
    """统一的错误日志记录"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_msg = f"[{timestamp}] {error_type}: {message}\n"
    if song_info:
        error_msg += f"歌曲信息: ID={song_info.get('id', 'Unknown')}, "
        error_msg += f"名称={song_info.get('name', 'Unknown')}, "
        error_msg += f"艺术家={song_info.get('ar', [{'name': 'Unknown'}])[0]['name']}\n"
    if details:
        error_msg += f"详细信息: {details}\n"
    error_msg += f"堆栈跟踪:\n{traceback.format_exc()}\n"
    error_msg += "-" * 80 + "\n"
    
    with open('fail.log', 'a', encoding='utf-8') as f:
        f.write(error_msg)

def check_api_response(response, error_msg="API请求失败"):
    """检查API响应"""
    try:
        response.raise_for_status()
        data = response.json()
        if not data:
            raise ValueError("API返回空数据")
        return data
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        error_details = {
            'url': response.url,
            'status_code': response.status_code,
            'response_text': response.text[:500]  # 只记录前500个字符
        }
        log_error("API错误", error_msg, error_details)
        raise

def safe_get_json(url, headers=None, timeout=10, error_msg=None):
    """安全的JSON请求"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return check_api_response(response, error_msg)
    except Exception as e:
        log_error("网络请求错误", str(e))
        raise

# 下载单首歌曲
def download_song(song_id, quality, folder_name, lyric_option):
    retries = 3
    song_info = None
    
    for attempt in range(retries):
        try:
            # 获取歌曲详情
            song_detail_url = f"{ncmapi}/song/detail?ids={song_id}"
            song_detail_res = safe_get_json(
                song_detail_url, 
                headers=headers, 
                error_msg=f"获取歌曲详情失败 (ID: {song_id})"
            )
            
            if 'songs' not in song_detail_res or not song_detail_res['songs']:
                raise KeyError("API响应中缺少'songs'字段或为空")
            
            song_info = song_detail_res['songs'][0]
            song_name = song_info['name']
            artist_name = song_info['ar'][0]['name']
            album_name = song_info['al']['name']
            album_pic_url = song_info['al']['picUrl']

            # 获取下载链接
            download_url = f"{ncmapi}/song/url/v1?id={song_id}&level={quality}"
            download_res = safe_get_json(
                download_url,
                headers=headers,
                error_msg=f"获取下载链接失败 (ID: {song_id})"
            )
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
            raw_lyrics = lyric_res.get('lrc', {}).get('lyric', '')
            lyrics = process_lyrics(raw_lyrics)

            # 设置文件扩展名
            ext = f".{type.lower()}"
            if ext not in ['.mp3', '.flac']:
                ext = '.mp3'  # 默认使用mp3

            # 下载歌曲
            song_filename = os.path.join(folder_name, f"{album_name} - {song_name} - {artist_name}{ext}")
            print(f"{YELLOW}正在下载{RESET}：{song_filename}")
            
            # 使用更小的块大小和错误处理
            try:
                with requests.get(song_url, headers=headers, stream=True) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    if total_size == 0:
                        raise ValueError("文件大小为0")
                    with open(song_filename, 'wb') as f, tqdm(
                        desc=f"{song_name} - {artist_name}",
                        total=total_size,
                        unit='MB',
                        unit_scale=True,
                        unit_divisor=1024 * 1024,
                    ) as bar:
                        chunk_size = 1024  # 减小块大小到1KB
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            retries = 3
                            for _ in range(retries):
                                try:
                                    size = f.write(chunk)
                                    bar.update(size / (1024 * 1024))
                                    break
                                except IOError as e:
                                    if _ == retries - 1:  # 最后一次尝试
                                        raise
                                    continue
            except Exception as e:
                log_error("文件下载错误", str(e), song_info=song_info)
                if os.path.exists(song_filename):
                    os.remove(song_filename)
                raise

            # 确保文件下载完成后再进行元数据注入
            if os.path.getsize(song_filename) == total_size:
                # 注入元数据
                try:
                    cover_data = requests.get(album_pic_url).content
                    inject_metadata(song_filename, song_info, lyrics, cover_data)
                except Exception as e:
                    log_error("元数据注入错误", str(e), song_info=song_info)
                    raise

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

        except Exception as e:
            log_error("下载处理错误", str(e), song_info=song_info)
            if attempt < retries - 1:
                print(f"{YELLOW}第{attempt + 1}次尝试失败，准备重试...{RESET}")
                continue
            else:
                raise

    return False

# 批量下载歌曲
def download_all(song_ids, folder_name, quality, lyric_option, max_workers):
    failed_songs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_song, sid, quality, folder_name, lyric_option): sid for sid in song_ids}
        for future in as_completed(futures):
            song_id = futures[future]
            try:
                if not future.result():
                    failed_songs.append(song_id)
            except Exception as e:
                log_error("批量下载错误", f"歌曲ID {song_id} 下载失败: {str(e)}")
                failed_songs.append(song_id)
    
    if failed_songs:
        print(f"\n{YELLOW}以下歌曲下载失败：{RESET}")
        for sid in failed_songs:
            print(f"- {sid}")
        print("详细错误信息请查看 fail.log")

def debug_response(response):
    """调试响应内容"""
    print(f"\n{YELLOW}Debug 信息:{RESET}")
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    print(f"响应内容: {response.text[:200]}...")  # 只显示前200个字符

def safe_request(url, error_prefix="请求失败"):
    """安全的请求处理"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        if not response.text:
            raise ValueError(f"{error_prefix}: 服务器返回空响应")
            
        try:
            return response.json()
        except json.JSONDecodeError:
            debug_response(response)
            raise ValueError(f"{error_prefix}: 服务器返回非JSON数据")
            
    except requests.exceptions.RequestException as e:
        print(f"{RED}{error_prefix}: {str(e)}{RESET}")
        raise
    except Exception as e:
        print(f"{RED}{error_prefix}: {str(e)}{RESET}")
        raise

# 主程序
download_type, id_value = choose_download_type()
quality = choose_quality()
lyric_option = choose_lyric_option()
max_workers = choose_concurrent_downloads()

if download_type == 'artist':
    try:
        print(f"{YELLOW}正在获取歌手专辑列表...{RESET}")
        artist_albums_url = f"{ncmapi}/artist/album?id={id_value}"
        artist_albums_res = safe_request(artist_albums_url, "获取歌手专辑列表失败")
        
        if not artist_albums_res.get('hotAlbums'):
            print(f"{YELLOW}未找到任何专辑。{RESET}")
            exit(0)

        albums = artist_albums_res['hotAlbums']
        print(f"{GREEN}找到 {len(albums)} 张专辑{RESET}")

        for album in albums:
            try:
                album_name = album['name']
                folder_name = f"{album['artist']['name']} - {album_name}"
                os.makedirs(folder_name, exist_ok=True)
                print(f"\n{GREEN}正在获取专辑 {album_name} 的曲目...{RESET}")

                album_tracks_url = f"{ncmapi}/album?id={album['id']}"
                album_tracks_res = safe_request(
                    album_tracks_url, 
                    f"获取专辑 {album_name} 曲目列表失败"
                )
                
                if not album_tracks_res.get('songs'):
                    print(f"{YELLOW}专辑 {album_name} 中未找到歌曲。{RESET}")
                    continue
                
                song_ids = [str(track['id']) for track in album_tracks_res['songs']]
                print(f"{GREEN}找到 {len(song_ids)} 首歌曲{RESET}")
                download_all(song_ids, folder_name, quality, lyric_option, max_workers)
                
            except Exception as e:
                log_error("专辑处理错误", str(e))
                print(f"{RED}处理专辑 {album_name} 时出错: {str(e)}{RESET}")
                continue

    except Exception as e:
        log_error("歌手专辑列表获取错误", str(e))
        print(f"{RED}获取歌手专辑列表失败: {str(e)}{RESET}")
        exit(1)

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