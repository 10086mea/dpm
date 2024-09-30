import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import requests
import re
import xml.dom.minidom
import sys
import os
import pandas as pd

################################################################
## Minghua Ji (https://minghuaji.dpm.org.cn/)
################################################################

# get gv info from url (minghuaji)
def get_info_mhj():
    gv_url = 'https://minghuaji.dpm.org.cn/js/gve.js'

    # get response from the url
    res_text = get_text_from_url(gv_url)

    # find all substrings surrounded by double quotes
    info = re.findall(r'"(.*?)"', res_text)

    # get key and iv from the substrings
    if len(info) < 5:
        raise ValueError(f'Encountered error when parsing {gv_url}')

    return info

# generate the dzi file
def generate_dzi_file_mhj(paint_id, info=None):
    paint_url = f'https://minghuaji.dpm.org.cn/paint/appreciate?id={paint_id}'
    html_string = get_text_from_url(paint_url)
    soup = BeautifulSoup(html_string, 'html.parser')
    image_items = soup.select_one('#gundong_id').find_all('li')

    # get info
    if info is None: info = get_info_mhj()

    # get key and vi and use them to decrypt the encrypted string
    #for i in range(len(info)): #输出info进行测试
    #    print(info2bytes(info[i]))
    key = info2bytes(info[3])
    iv = info2bytes(info[5])

    for idx, item in enumerate(image_items):
        paint_detail_url = f'{paint_url}&type={item.get("value")}'

        encrypted = get_encrypted_text(paint_detail_url)
        decrypted = decrypt(encrypted, key, iv)

        # get xmlns and overlap
        xmlns = info2bytes(info[29]).decode('utf-8')
        overlap = info2bytes(info[30]).decode('utf-8')

        # create dzi file
        dzi_info = {
            'xmlns': xmlns,
            'url': decrypted[2],
            'overlap': decrypted[5],
            'tilesize': decrypted[1],
            'format': decrypted[0],
            'width': str(int(float(decrypted[4]))),
            'height': str(int(float(decrypted[3]))) #修改了列表索引 2024年9月30日
        }
        if len(image_items) == 1:
            dzi_filename = f'{paint_id}.dzi'
        else:
            dzi_filename = f'{paint_id}_{idx}.dzi'
        write_dzi_file(dzi_filename, dzi_info)

################################################################
## Collection (https://www.dpm.org.cn/explore/collections.html)
################################################################

# get dzi info from an uncommon type of url
def get_dzi_info_bigimg(url):
    html_string = get_text_from_url(url)
    soup = BeautifulSoup(html_string, 'html.parser')
    script = soup.find_all('script')[-1].text

    if not 'OpenSeadragon' in script:
        raise ValueError(f'Cannot find OpenSeadragon in {url}')
    script = script.split('tileSources:')[1]
    keys = ['xmlns', 'Url', 'Overlap', 'TileSize', 'Format', 'Width', 'Height']
    dzi_info = {}
    for key in keys:
        value = re.search(rf'{key}:\s*"(.*?)",', script).group(1)
        dzi_info[key.lower()] = value

    return dzi_info


def generate_dzi_file_collection(paint_id):
    url = f'https://www.dpm.org.cn/collection/paint/{paint_id}.html'
    html_string = get_text_from_url(url)
    soup = BeautifulSoup(html_string, 'html.parser')

    # get dzi url
    #item = soup.select_one('#hl_content')
    image_items = soup.find_all('img', {'custom_tilegenerator': re.compile(r'http://en.dpm.org.cn/.*')})

    tilegenerator_urls = [item.get('custom_tilegenerator').replace('dyx.html?path=/', '') for item in image_items]
    # remove duplicates
    tilegenerator_urls =pd.Series(tilegenerator_urls).drop_duplicates().tolist()

    for idx, tilegenerator_url in enumerate(tilegenerator_urls):
        if not 'bigimg' in tilegenerator_url:
            tilegenerator = get_text_from_url(tilegenerator_url)

            # get dzi info
            root = ET.fromstring(tilegenerator)
            dzi_info = {
                'xmlns': root.attrib['xmnls'],
                'url': tilegenerator_url.replace('http:','https:').replace('.xml', '_files/'),
                'overlap': root.attrib['Overlap'],
                'tilesize': root.attrib['TileSize'],
                'format': root.attrib['Format'],
                'width': root[0].attrib['Width'],
                'height': root[0].attrib['Height']
            }
        else:
            dzi_info = get_dzi_info_bigimg(tilegenerator_url)

        if len(image_items) == 1:
            dzi_filename = f'{paint_id}.dzi'
        else:
            dzi_filename = f'{paint_id}_{idx}.dzi'
        write_dzi_file(dzi_filename, dzi_info)


################################################################
## Digital Catalog (https://digicol.dpm.org.cn/)
################################################################

# get gv info from url (digicol)
def get_info_digicol():
    gv_url = 'https://digicol.dpm.org.cn/js/gve.js'

    # get response from the url
    res_text = get_text_from_url(gv_url)

    info = re.findall(r'"(.*?)"', res_text)[3]
    info = info2bytes(info).decode('utf-8').split('|')

    return info

# generate the dzi file
def generate_dzi_file_digicol(paint_id, info=None):
    paint_url = f'https://digicol.dpm.org.cn/cultural/listCulturalImage?id={paint_id}'
    html_string = get_text_from_url(paint_url)
    soup = BeautifulSoup(html_string, 'html.parser')

    # get image id
    image_id = soup.select_one('#swiper-wrapper-img').select_one('div').get('value')

    # get info
    if info is None: info = get_info_digicol()

    # get key and vi and use them to decrypt the encrypted string
    key = info[35].encode('utf-8')
    iv = info[45].encode('utf-8')

    paint_detail_url = f'https://digicol.dpm.org.cn/cultural/details?id={image_id}'

    encrypted = get_encrypted_text(paint_detail_url)
    decrypted = decrypt(encrypted, key, iv)

    # create dzi file
    dzi_info = {
        'xmlns': 'http://schemas.microsoft.com/deepzoom/2009',
        'url': decrypted[0],
        'overlap': '1',
        'tilesize': decrypted[4],
        'format': decrypted[1],
        'width': str(int(float(decrypted[2]))),
        'height': str(int(float(decrypted[3])))
    }

    dzi_filename = f'{paint_id}.dzi'
    write_dzi_file(dzi_filename, dzi_info)


################################################################
## common functions
################################################################

# get text from url
def get_text_from_url(url):

    # get response from the url
    res = requests.get(url)

    # check for successful request
    if res.status_code != 200:
        raise ValueError(f'Encountered error when visiting {url}: {res.status_code}')

    return res.text

# convert info to bytes
def info2bytes(info):
    return bytes.fromhex(info.replace('\\x',''))

# decrypt the encrypted string
def decrypt(encrypted, key, iv):
    # create cipher object
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # decrypt the encrypted string
    decrypted = cipher.decrypt(base64.b64decode(encrypted))
    decrypted = unpad(decrypted, 16).decode('utf-8').split('^')

    return decrypted

# get the encrypted string from the paint url
def get_encrypted_text(paint_url):
    # get response from the url
    res_text = get_text_from_url(paint_url)

    # find the first substring that matches the encrypted string
    match = re.search(r'gv.init\("(.*?)"', res_text)
    if match:
        encrypted = match.group(1)
        return encrypted
    else:
        raise ValueError(f'Cannot find encrypted string in {paint_url}')

def generate_dzi_file(website, paint_id, info=None):
    if website == 'mhj':
        generate_dzi_file_mhj(paint_id, info)
    elif website == 'collection':
        generate_dzi_file_collection(paint_id)
    elif website == 'digicol':
        generate_dzi_file_digicol(paint_id, info)
    else:
        raise ValueError(f'Unknown website {website}')

def write_dzi_file(dzi_filename, dzi_info):
    # check if paintings folder exists
    if not os.path.exists('paintings'):
        os.makedirs('paintings')

    # create dzi file
    file = open(f'paintings/{dzi_filename}', 'wb')
    doc = xml.dom.minidom.Document()
    image = doc.createElementNS(dzi_info['xmlns'], 'Image')
    image.setAttribute('xmlns', dzi_info['xmlns'])
    image.setAttribute('Url', dzi_info['url'])
    image.setAttribute('Overlap', dzi_info['overlap'])
    image.setAttribute('TileSize', dzi_info['tilesize'])
    image.setAttribute('Format', dzi_info['format'])
    size = doc.createElementNS(dzi_info['xmlns'], 'Size')
    size.setAttribute('Width', dzi_info['width'])
    size.setAttribute('Height', dzi_info['height'])
    image.appendChild(size)
    doc.appendChild(image)
    descriptor = doc.toxml(encoding='UTF-8')
    file.write(descriptor)
    file.close()

# get gv info from url
def get_info(website):
    if website == 'mhj':
        return get_info_mhj()
    elif website == 'collection':
        return None
    elif website == 'digicol':
        return get_info_digicol()

if __name__ == '__main__':
    # create the directory to store the dzi files
    if not os.path.exists('paintings'): os.makedirs('paintings')

    website = sys.argv[1]
    paint_id = sys.argv[2]

    generate_dzi_file(website=website, id=paint_id)
