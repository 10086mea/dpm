import pandas as pd
import subprocess
import os
import sys
import re
import glob
from generate_dzi import generate_dzi_file, get_info

def download_image(website, paint_id, info=None, download_largest=True):
    # 检查是否存在 .dzi 文件
    dzi_files = glob.glob(f'paintings/{paint_id}*.dzi')
    if len(dzi_files) == 0:
        try:
            generate_dzi_file(website, paint_id, info=info)
            # 再次检查是否生成了 .dzi 文件
            dzi_files = glob.glob(f'paintings/{paint_id}*.dzi')
            if len(dzi_files) == 0:
                print(f'No .dzi files found for painting {paint_id} after generation.')
                return
        except Exception as e:
            print(f'Failed to generate dzi files for painting {paint_id}: {e}')
            # 清理文件
            dzi_files = glob.glob(f'paintings/{paint_id}*.dzi')
            for dzi_file in dzi_files: os.remove(dzi_file)
            return

    # 再次检查 dzi_files 是否为空
    if not dzi_files:
        print(f'No .dzi files found for painting {paint_id}. Skipping.')
        return

    try:
        with open(dzi_files[0], 'r') as f:
            content = f.read()
        match = re.search('Format="(\w+)"', content)
        if match:
            format = match.group(1)
        else:
            print(f'No format found in {dzi_files[0]}. Skipping.')
            return
    except Exception as e:
        print(f'Error reading {dzi_files[0]}: {e}')
        return

    for dzi_file in dzi_files:
        paint_file = dzi_file.replace('.dzi', f'.{format}')

        # 检查图片是否已存在
        if os.path.exists(paint_file):
            print(f'Painting {paint_file} already exists.')
            continue

        # dezoomify-rs
        dezoomify = './dezoomify-rs'
        if not os.path.isfile(dezoomify):
            dezoomify = 'dezoomify-rs'  # 假设在 PATH 中

        command = f'{dezoomify} --dezoomer deepzoom "{dzi_file}" --header "Referer: https://www.dpm.org.cn" --retries 1 {"--largest " if download_largest else ""}{paint_file}'
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f'Failed to download {paint_file}: {e}')

def download_all(website):
    # 从 CSV 读取绘画 ID
    try:
        df = pd.read_csv('paintings.csv')
    except Exception as e:
        print(f'Failed to read paintings.csv: {e}')
        return

    info = get_info(website)
    for index, row in df.iterrows():
        paint_id = row['id']
        print(f'Painting {paint_id} ({index + 1}/{len(df)}) ...')
        download_image(website, paint_id, info=info, download_largest=True)

if __name__ == '__main__':
    website = sys.argv[1]

    # 创建目录（如果不存在）
    if not os.path.exists('paintings'):
        try:
            os.makedirs('paintings')
        except Exception as e:
            print(f'Failed to create directory "paintings": {e}')
            sys.exit(1)

    download_all(website)
