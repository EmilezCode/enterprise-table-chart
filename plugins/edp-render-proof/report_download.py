"""Save an authorized report on this connector's own computer, never the server."""
from pathlib import Path
import hashlib
import re


def save_report(file, directory=None):
    name=file.get('name','')
    if not re.fullmatch(r'企业表图(?:业务报告|明细|摘要)-[0-9a-f]{8}\.(?:md|csv)',name):
        raise ValueError('报告文件名无效，未保存。')
    text=file.get('text')
    if not isinstance(text,str) or not text:
        raise ValueError('报告内容为空，未保存。')
    folder=Path(directory) if directory is not None else Path.home()/'Downloads'
    folder.mkdir(parents=True,exist_ok=True)
    body=text.encode('utf8')
    for number in range(1000):
        path=folder/(name if not number else f'{Path(name).stem} ({number}){Path(name).suffix}')
        try:
            with path.open('xb') as stream:
                stream.write(body)
            return {'status':'FILE_SAVED','filename':path.name,'path':str(path),
                    'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
        except FileExistsError:
            continue
    raise ValueError('同名报告过多，请整理下载目录后再保存。')
