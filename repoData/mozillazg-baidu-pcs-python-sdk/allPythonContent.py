__FILENAME__ = api
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import wraps
import json
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import requests
from requests_toolbelt import MultipartEncoder

API_TEMPLATE = 'https://pcs.baidu.com/rest/2.0/pcs/{0}'


class InvalidToken(Exception):
    """异常：Access Token 不正确或者已经过期."""
    pass


def check_token(func):
    """检查 access token 是否有效."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code == 401:
            raise InvalidToken('Access token invalid or no longer valid')
        else:
            return response
    return wrapper


class BaseClass(object):
    def __init__(self, access_token, api_template=API_TEMPLATE):
        self.access_token = access_token
        self.api_template = api_template

    def _remove_empty_items(self, data):
        for k, v in data.copy().items():
            if v is None:
                data.pop(k)

    @check_token
    def _request(self, uri, method, url=None, extra_params=None,
                 data=None, files=None, **kwargs):
        params = {
            'method': method,
            'access_token': self.access_token
        }
        if extra_params:
            params.update(extra_params)
            self._remove_empty_items(params)

        if not url:
            url = self.api_template.format(uri)
        api = url

        if data or files:
            api = '%s?%s' % (url, urlencode(params))
            if data:
                self._remove_empty_items(data)
            else:
                self._remove_empty_items(files)
                data = MultipartEncoder(files)
                if kwargs.get('headers'):
                    kwargs['headers']['Content-Type'] = data.content_type
                else:
                    kwargs['headers'] = {'Content-Type': data.content_type}
            response = requests.post(api, data=data, **kwargs)
        else:
            response = requests.get(api, params=params, **kwargs)
        return response


class PCS(BaseClass):
    """百度个人云存储（PCS）Python SDK.

    所有 api 方法的返回值均为 ``requests.Response`` 对象::

      >>> pcs = PCS('access_token')
      >>> response = pcs.info()
      >>> response
      <Response [200]>
      >>> response.ok  # 状态码是否是 200
      True
      >>> response.status_code  # 状态码
      200
      >>> response.content  # 原始内容（二进制/json 字符串）
      '{"quota":6442450944,"used":5138887,"request_id":1216061570}'
      >>>
      >>> response.json()  # 将 json 字符串转换为 python dict
      {u'used': 5138887, u'quota': 6442450944L, u'request_id': 1216061570}
    """
    def info(self, **kwargs):
        """获取当前用户空间配额信息.

        :return: Response 对象
        """

        return self._request('quota', 'info', **kwargs)

    def upload(self, remote_path, file_content, ondup=None, **kwargs):
        """上传单个文件（<2G）.

        | 百度PCS服务目前支持最大2G的单个文件上传。
        | 如需支持超大文件（>2G）的断点续传，请参考下面的“分片文件上传”方法。

        :param remote_path: 网盘中文件的保存路径（包含文件名）。
                            必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param file_content: 上传文件的内容/文件对象 。
                             (e.g. ``open('foobar', 'rb')`` )
        :param ondup: （可选）

                      * 'overwrite'：表示覆盖同名文件；
                      * 'newcopy'：表示生成文件副本并进行重命名，命名规则为“
                        文件名_日期.后缀”。
        :return: Response 对象
        """

        params = {
            'path': remote_path,
            'ondup': ondup
        }
        files = {'file': ('file', file_content, '')}
        url = 'https://c.pcs.baidu.com/rest/2.0/pcs/file'
        return self._request('file', 'upload', url=url, extra_params=params,
                             files=files, **kwargs)

    def upload_tmpfile(self, file_content, **kwargs):
        """分片上传—文件分片及上传.

        百度 PCS 服务支持每次直接上传最大2G的单个文件。

        如需支持上传超大文件（>2G），则可以通过组合调用分片文件上传的
        ``upload_tmpfile`` 方法和 ``upload_superfile`` 方法实现：

        1. 首先，将超大文件分割为2G以内的单文件，并调用 ``upload_tmpfile``
           将分片文件依次上传；
        2. 其次，调用 ``upload_superfile`` ，完成分片文件的重组。

        除此之外，如果应用中需要支持断点续传的功能，
        也可以通过分片上传文件并调用 ``upload_superfile`` 接口的方式实现。

        :param file_content: 上传文件的内容/文件对象
                             (e.g. ``open('foobar', 'rb')`` )
        :return: Response 对象
        """

        params = {
            'type': 'tmpfile'
        }
        files = {'file': ('file', file_content, '')}
        url = 'https://c.pcs.baidu.com/rest/2.0/pcs/file'
        return self._request('file', 'upload', url=url, extra_params=params,
                             files=files, **kwargs)

    def upload_superfile(self, remote_path, block_list, ondup=None, **kwargs):
        """分片上传—合并分片文件.

        与分片文件上传的 ``upload_tmpfile`` 方法配合使用，
        可实现超大文件（>2G）上传，同时也可用于断点续传的场景。

        :param remote_path: 网盘中文件的保存路径（包含文件名）。
                            必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param block_list: 子文件内容的 MD5 值列表；子文件至少两个，最多1024个。
        :type block_list: list
        :param ondup: （可选）

                      * 'overwrite'：表示覆盖同名文件；
                      * 'newcopy'：表示生成文件副本并进行重命名，命名规则为“
                        文件名_日期.后缀”。
        :return: Response 对象
        """

        params = {
            'path': remote_path,
            'ondup': ondup
        }
        data = {
            'param': json.dumps({'block_list': block_list}),
        }
        return self._request('file', 'createsuperfile', extra_params=params,
                             data=data, **kwargs)

    def download(self, remote_path, **kwargs):
        """下载单个文件。

        download 接口支持HTTP协议标准range定义，通过指定range的取值可以实现
        断点下载功能。 例如：如果在request消息中指定“Range: bytes=0-99”，
        那么响应消息中会返回该文件的前100个字节的内容；
        继续指定“Range: bytes=100-199”，
        那么响应消息中会返回该文件的第二个100字节内容::

          >>> headers = {'Range': 'bytes=0-99'}
          >>> pcs = PCS('token')
          >>> pcs.download('/apps/test_sdk/test.txt', headers=headers)

        :param remote_path: 网盘中文件的路径（包含文件名）。
                            必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象
        """

        params = {
            'path': remote_path,
        }
        url = 'https://d.pcs.baidu.com/rest/2.0/pcs/file'
        return self._request('file', 'download', url=url,
                             extra_params=params, **kwargs)

    def mkdir(self, remote_path, **kwargs):
        """为当前用户创建一个目录.

        :param remote_path: 网盘中目录的路径，必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象
        """

        data = {
            'path': remote_path
        }
        return self._request('file', 'mkdir', data=data, **kwargs)

    def meta(self, remote_path, **kwargs):
        """获取单个文件或目录的元信息.

        :param remote_path: 网盘中文件/目录的路径，必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象
        """

        params = {
            'path': remote_path
        }
        return self._request('file', 'meta', extra_params=params, **kwargs)

    def multi_meta(self, path_list, **kwargs):
        """批量获取文件或目录的元信息.

        :param path_list: 网盘中文件/目录的路径列表，路径必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type path_list: list
        :return: Response 对象
        """

        data = {
            'param': json.dumps({
                'list': [{'path': path} for path in path_list]
            }),
        }
        return self._request('file', 'meta', data=data, **kwargs)

    def list_files(self, remote_path, by=None, order=None,
                   limit=None, **kwargs):
        """获取目录下的文件列表.

        :param remote_path: 网盘中目录的路径，必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param by: 排序字段，缺省根据文件类型排序：

                   * time（修改时间）
                   * name（文件名）
                   * size（大小，注意目录无大小）
        :param order: “asc”或“desc”，缺省采用降序排序。

                      * asc（升序）
                      * desc（降序）
        :param limit: 返回条目控制，参数格式为：n1-n2。

                      返回结果集的[n1, n2)之间的条目，缺省返回所有条目；
                      n1从0开始。
        :return: Response 对象
        """

        params = {
            'path': remote_path,
            'by': by,
            'order': order,
            'limit': limit
        }
        return self._request('file', 'list', extra_params=params, **kwargs)

    def move(self, from_path, to_path, **kwargs):
        """移动单个文件或目录.

        :param from_path: 源文件/目录在网盘中的路径（包括文件名）。

                          .. warning::
                              * 路径长度限制为1000；
                              * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                              * 文件名或路径名开头结尾不能是 ``.``
                                或空白字符，空白字符包括：
                                ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param to_path: 目标文件/目录在网盘中的路径（包括文件名）。

                        .. warning::
                            * 路径长度限制为1000；
                            * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                            * 文件名或路径名开头结尾不能是 ``.``
                              或空白字符，空白字符包括：
                              ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象
        """

        data = {
            'from': from_path,
            'to': to_path,
        }
        return self._request('file', 'move', data=data, **kwargs)

    def multi_move(self, path_list, **kwargs):
        """批量移动文件或目录.

        :param path_list: 源文件地址和目标文件地址对列表:

                          >>> path_list = [
                          ...   ('/apps/test_sdk/test.txt',  # 源文件
                          ...    '/apps/test_sdk/testmkdir/b.txt'  # 目标文件
                          ...   ),
                          ...   ('/apps/test_sdk/test.txt',  # 源文件
                          ...    '/apps/test_sdk/testmkdir/b.txt'  # 目标文件
                          ...   ),
                          ... ]

                          .. warning::
                              * 路径长度限制为1000；
                              * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                              * 文件名或路径名开头结尾不能是 ``.``
                                或空白字符，空白字符包括：
                                ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type path_list: list
        :return: Response 对象
        """

        data = {
            'param': json.dumps({
                'list': [{'from': x[0], 'to': x[1]} for x in path_list]
            }),
        }
        return self._request('file', 'move', data=data, **kwargs)

    def copy(self, from_path, to_path, **kwargs):
        """拷贝文件或目录.

        :param from_path: 源文件/目录在网盘中的路径（包括文件名）。

                          .. warning::
                              * 路径长度限制为1000；
                              * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                              * 文件名或路径名开头结尾不能是 ``.``
                                或空白字符，空白字符包括：
                                ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param to_path: 目标文件/目录在网盘中的路径（包括文件名）。

                        .. warning::
                            * 路径长度限制为1000；
                            * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                            * 文件名或路径名开头结尾不能是 ``.``
                              或空白字符，空白字符包括：
                              ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象

        .. warning::
           ``move`` 操作后，源文件被移动至目标地址；
           ``copy`` 操作则会保留原文件。
        """

        data = {
            'from': from_path,
            'to': to_path,
        }
        return self._request('file', 'copy', data=data, **kwargs)

    def multi_copy(self, path_list, **kwargs):
        """批量拷贝文件或目录.

        :param path_list: 源文件地址和目标文件地址对的列表:

                          >>> path_list = [
                          ...   ('/apps/test_sdk/test.txt',  # 源文件
                          ...    '/apps/test_sdk/testmkdir/b.txt'  # 目标文件
                          ...   ),
                          ...   ('/apps/test_sdk/test.txt',  # 源文件
                          ...    '/apps/test_sdk/testmkdir/b.txt'  # 目标文件
                          ...   ),
                          ... ]

                          .. warning::
                              * 路径长度限制为1000；
                              * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                              * 文件名或路径名开头结尾不能是 ``.``
                                或空白字符，空白字符包括：
                                ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type path_list: list
        :return: Response 对象
        """

        data = {
            'param': json.dumps({
                'list': [{'from': x[0], 'to': x[1]} for x in path_list]
            }),
        }
        return self._request('file', 'copy', data=data, **kwargs)

    def delete(self, remote_path, **kwargs):
        """删除单个文件或目录.

        .. warning::
           * 文件/目录删除后默认临时存放在回收站内，删除文件或目录的临时存放
             不占用用户的空间配额；
           * 存放有效期为10天，10天内可还原回原路径下，10天后则永久删除。

        :param remote_path: 网盘中文件/目录的路径，路径必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type remote_path: str
        :return: Response 对象
        """

        data = {
            'path': remote_path
        }
        return self._request('file', 'delete', data=data, **kwargs)

    def multi_delete(self, path_list, **kwargs):
        """批量删除文件或目录.

        .. warning::
           * 文件/目录删除后默认临时存放在回收站内，删除文件或目录的临时存放
             不占用用户的空间配额；
           * 存放有效期为10天，10天内可还原回原路径下，10天后则永久删除。

        :param path_list: 网盘中文件/目录的路径列表，路径必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type path_list: list
        :return: Response 对象
        """

        data = {
            'param': json.dumps({
                'list': [{'path': path} for path in path_list]
            }),
        }
        return self._request('file', 'delete', data=data, **kwargs)

    def search(self, remote_path, keyword, recurrent='0', **kwargs):
        """按文件名搜索文件（不支持查找目录）.

        :param remote_path: 需要检索的目录路径，路径必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type remote_path: str
        :param keyword: 关键词
        :type keyword: str
        :param recurrent: 是否递归。

                          * "0"表示不递归
                          * "1"表示递归
        :type recurrent: str
        :return: Response 对象
        """

        params = {
            'path': remote_path,
            'wd': keyword,
            're': recurrent,
        }
        return self._request('file', 'search', extra_params=params, **kwargs)

    def thumbnail(self, remote_path, height, width, quality=100, **kwargs):
        """获取指定图片文件的缩略图.

        :param remote_path: 源图片的路径，路径必须以 /apps/ 开头。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param height: 指定缩略图的高度，取值范围为(0,1600]。
        :type height: int
        :param width: 指定缩略图的宽度，取值范围为(0,1600]。
        :type width: int
        :param quality: 缩略图的质量，默认为100，取值范围(0,100]。
        :type quality: int
        :return: Response 对象

        .. warning::
           有以下限制条件：

           * 原图大小(0, 10M]；
           * 原图类型: jpg、jpeg、bmp、gif、png；
           * 目标图类型:和原图的类型有关；例如：原图是gif图片，
             则缩略后也为gif图片。
        """

        params = {
            'path': remote_path,
            'height': height,
            'width': width,
            'quality': quality,
        }
        return self._request('thumbnail', 'generate', extra_params=params,
                             **kwargs)

    def diff(self, cursor='null', **kwargs):
        """文件增量更新操作查询接口.
        本接口有数秒延迟，但保证返回结果为最终一致.

        :param cursor: 用于标记更新断点。

                       * 首次调用cursor=null；
                       * 非首次调用，使用最后一次调用diff接口的返回结果
                         中的cursor。
        :type cursor: str
        :return: Response 对象
        """

        params = {
            'cursor': cursor,
        }
        return self._request('file', 'diff', extra_params=params, **kwargs)

    def video_convert(self, remote_path, video_type, **kwargs):
        """对视频文件进行转码，实现实时观看视频功能.
        可下载支持 HLS/M3U8 的 `媒体云播放器 SDK <HLSSDK_>`__ 配合使用.

        .. _HLSSDK:
           http://developer.baidu.com/wiki/index.php?title=docs/cplat/media/sdk

        :param remote_path: 需要下载的视频文件路径，以/开头的绝对路径，
                            需含源文件的文件名。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :type remote_path: str
        :param video_type: 目前支持以下格式：
                           M3U8_320_240、M3U8_480_224、M3U8_480_360、
                           M3U8_640_480和M3U8_854_480
        :type video_type: str
        :return: Response 对象

        .. warning::
           目前这个接口支持的源文件格式如下：

           +--------------------------+------------+--------------------------+
           |格式名称                  |扩展名      |备注                      |
           +==========================+============+==========================+
           |Apple HTTP Live Streaming |m3u8/m3u    |iOS支持的视频格式         |
           +--------------------------+------------+--------------------------+
           |ASF                       |asf         |视频格式                  |
           +--------------------------+------------+--------------------------+
           |AVI                       |avi         |视频格式                  |
           +--------------------------+------------+--------------------------+
           |Flash Video (FLV)         |flv         |Macromedia Flash视频格式  |
           +--------------------------+------------+--------------------------+
           |GIF Animation             |gif         |视频格式                  |
           +--------------------------+------------+--------------------------+
           |Matroska                  |mkv         |Matroska/WebM视频格式     |
           +--------------------------+------------+--------------------------+
           |MOV/QuickTime/MP4         |mov/mp4/m4a/|支持3GP、3GP2、PSP、iPod  |
           |                          |3gp/3g2/mj2 |之类视频格式              |
           +--------------------------+------------+--------------------------+
           |MPEG-PS (program stream)  |mpeg        |也就是VOB文件/SVCD/DVD格式|
           +--------------------------+------------+--------------------------+
           |MPEG-TS (transport stream)|ts          | 即DVB传输流              |
           +--------------------------+------------+--------------------------+
           |RealMedia                 |rm/rmvb     | Real视频格式             |
           +--------------------------+------------+--------------------------+
           |WebM                      |webm        | Html视频格式             |
           +--------------------------+------------+--------------------------+
        """

        params = {
            'path': remote_path,
            'type': video_type,
        }
        return self._request('file', 'streaming', extra_params=params,
                             **kwargs)

    def list_streams(self, file_type, start=0, limit=100,
                     filter_path=None, **kwargs):
        """以视频、音频、图片及文档四种类型的视图获取所创建应用程序下的
        文件列表.

        :param file_type: 类型分为video、audio、image及doc四种。
        :param start: 返回条目控制起始值，缺省值为0。
        :param limit: 返回条目控制长度，缺省为1000，可配置。
        :param filter_path: 需要过滤的前缀路径，如：/apps/album

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象
        """

        params = {
            'type': file_type,
            'start': start,
            'limit': limit,
            'filter_path': filter_path,
        }
        return self._request('stream', 'list', extra_params=params,
                             **kwargs)

    def download_stream(self, remote_path, **kwargs):
        """为当前用户下载一个流式文件.其参数和返回结果与下载单个文件的相同.

        :param remote_path: 需要下载的文件路径，以/开头的绝对路径，含文件名。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :return: Response 对象
        """

        params = {
            'path': remote_path,
        }
        url = 'https://d.pcs.baidu.com/rest/2.0/pcs/file'
        return self._request('stream', 'download', url=url,
                             extra_params=params, **kwargs)

    def rapid_upload(self, remote_path, content_length, content_md5,
                     content_crc32, slice_md5, ondup=None, **kwargs):
        """秒传一个文件.

        .. warning::
           * 被秒传文件必须大于256KB（即 256*1024 B）。
           * 校验段为文件的前256KB，秒传接口需要提供校验段的MD5。
             (非强一致接口，上传后请等待1秒后再读取)

        :param remote_path: 上传文件的全路径名。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param content_length: 待秒传文件的长度。
        :param content_md5: 待秒传文件的MD5。
        :param content_crc32: 待秒传文件的CRC32。
        :param slice_md5: 待秒传文件校验段的MD5。
        :param ondup: （可选）

                      * 'overwrite'：表示覆盖同名文件；
                      * 'newcopy'：表示生成文件副本并进行重命名，命名规则为“
                        文件名_日期.后缀”。
        :return: Response 对象
        """
        data = {
            'path': remote_path,
            'content-length': content_length,
            'content-md5': content_md5,
            'content-crc32': content_crc32,
            'slice-md5': slice_md5,
            'ondup': ondup,
        }
        return self._request('file', 'rapidupload', data=data, **kwargs)

    def add_download_task(self, source_url, remote_path,
                          rate_limit=None, timeout=60 * 60,
                          expires=None, callback='', **kwargs):
        """添加离线下载任务，实现单个文件离线下载.

        :param source_url: 源文件的URL。
        :param remote_path: 下载后的文件保存路径。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param rate_limit: 下载限速，默认不限速。
        :type rate_limit: int or long
        :param timeout: 下载超时时间，默认3600秒。
        :param expires: 请求失效时间，如果有，则会校验。
        :type expires: int
        :param callback: 下载完毕后的回调，默认为空。
        :type callback: str
        :return: Response 对象
        """

        data = {
            'source_url': source_url,
            'save_path': remote_path,
            'expires': expires,
            'rate_limit': rate_limit,
            'timeout': timeout,
            'callback': callback,
        }
        return self._request('services/cloud_dl', 'add_task',
                             data=data, **kwargs)

    def query_download_tasks(self, task_ids, operate_type=1,
                             expires=None, **kwargs):
        """根据任务ID号，查询离线下载任务信息及进度信息。

        :param task_ids: 要查询的任务ID列表
        :type task_ids: list or tuple
        :param operate_type:
                            * 0：查任务信息
                            * 1：查进度信息，默认为1
        :param expires: 请求失效时间，如果有，则会校验。
        :type expires: int
        :return: Response 对象
        """

        params = {
            'task_ids': ','.join(map(str, task_ids)),
            'op_type': operate_type,
            'expires': expires,
        }
        return self._request('services/cloud_dl', 'query_task',
                             extra_params=params, **kwargs)

    def list_download_tasks(self, need_task_info=1, start=0, limit=10, asc=0,
                            create_time=None, status=None, source_url=None,
                            remote_path=None, expires=None, **kwargs):
        """查询离线下载任务ID列表及任务信息.

        :param need_task_info: 是否需要返回任务信息:

                               * 0：不需要
                               * 1：需要，默认为1
        :param start: 查询任务起始位置，默认为0。
        :param limit: 设定返回任务数量，默认为10。
        :param asc:

                   * 0：降序，默认值
                   * 1：升序
        :param create_time: 任务创建时间，默认为空。
        :type create_time: int
        :param status: 任务状态，默认为空。
                       0:下载成功，1:下载进行中 2:系统错误，3:资源不存在，
                       4:下载超时，5:资源存在但下载失败, 6:存储空间不足,
                       7:目标地址数据已存在, 8:任务取消.
        :type status: int
        :param source_url: 源地址URL，默认为空。
        :param remote_path: 文件保存路径，默认为空。

                            .. warning::
                                * 路径长度限制为1000；
                                * 径中不能包含以下字符：``\\\\ ? | " > < : *``；
                                * 文件名或路径名开头结尾不能是 ``.``
                                  或空白字符，空白字符包括：
                                  ``\\r, \\n, \\t, 空格, \\0, \\x0B`` 。
        :param expires: 请求失效时间，如果有，则会校验。
        :type expires: int
        :return: Response 对象
        """

        data = {
            'expires': expires,
            'start': start,
            'limit': limit,
            'asc': asc,
            'source_url': source_url,
            'save_path': remote_path,
            'create_time': create_time,
            'status': status,
            'need_task_info': need_task_info,
        }
        return self._request('services/cloud_dl', 'list_task',
                             data=data, **kwargs)

    def cancel_download_task(self, task_id, expires=None, **kwargs):
        """取消离线下载任务.

        :param task_id: 要取消的任务ID号。
        :type task_id: str
        :param expires: 请求失效时间，如果有，则会校验。
        :type expires: int
        :return: Response 对象
        """

        data = {
            'expires': expires,
            'task_id': task_id,
        }
        return self._request('services/cloud_dl', 'cancle_task',
                             data=data, **kwargs)

    def list_recycle_bin(self, start=0, limit=1000, **kwargs):
        """获取回收站中的文件及目录列表.

        :param start: 返回条目的起始值，缺省值为0
        :param limit: 返回条目的长度，缺省值为1000
        :return: Response 对象
        """

        params = {
            'start': start,
            'limit': limit,
        }
        return self._request('file', 'listrecycle',
                             extra_params=params, **kwargs)

    def restore_recycle_bin(self, fs_id, **kwargs):
        """还原单个文件或目录（非强一致接口，调用后请sleep 1秒读取）.

        :param fs_id: 所还原的文件或目录在PCS的临时唯一标识ID。
        :type fs_id: str
        :return: Response 对象
        """

        data = {
            'fs_id': fs_id,
        }
        return self._request('file', 'restore', data=data, **kwargs)

    def multi_restore_recycle_bin(self, fs_ids, **kwargs):
        """批量还原文件或目录（非强一致接口，调用后请sleep1秒 ）.

        :param fs_ids: 所还原的文件或目录在 PCS 的临时唯一标识 ID 的列表。
        :type fs_ids: list or tuple
        :return: Response 对象
        """

        data = {
            'param': json.dumps({
                'list': [{'fs_id': fs_id} for fs_id in fs_ids]
            }),
        }
        return self._request('file', 'restore', data=data, **kwargs)

    def clean_recycle_bin(self, **kwargs):
        """清空回收站.

        :return: Response 对象
        """

        data = {
            'type': 'recycle',
        }
        return self._request('file', 'delete', data=data, **kwargs)

########NEW FILE########
__FILENAME__ = tools
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests


def get_new_access_token(refresh_token, client_id, client_secret,
                         scope=None, **kwargs):
    """使用 Refresh Token 刷新以获得新的 Access Token.

    :param refresh_token: 用于刷新 Access Token 用的 Refresh Token；
    :param client_id: 应用的 API Key；
    :param client_secret: 应用的 Secret Key;
    :param scope: 以空格分隔的权限列表，若不传递此参数，代表请求的数据访问
                  操作权限与上次获取 Access Token 时一致。通过 Refresh Token
                  刷新 Access Token 时所要求的 scope 权限范围必须小于等于上次
                  获取 Access Token 时授予的权限范围。 关于权限的具体信息请参考
                  “ `权限列表`__ ”。
    :return: Response 对象

    关于 ``response.json()`` 字典的内容所代表的含义，
    请参考 `相关的百度帮助文档`__ 。

     __ http://developer.baidu.com/wiki/index.php?title=docs/oauth/baiduoauth/list
     __ http://developer.baidu.com/wiki/index.php?title=docs/oauth/refresh
    """
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
    }
    if scope:
        data['scope'] = scope
    url = 'https://openapi.baidu.com/oauth/2.0/token'
    return requests.post(url, data=data)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# BaiduPCS documentation build configuration file, created by
# sphinx-quickstart on Fri Sep 06 22:22:13 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../baidupcs'))


# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'BaiduPCS'
copyright = '2014, mozillazg'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3.2'
# The full version, including alpha/beta/rc tags.
release = '0.3.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'BaiduPCSdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'BaiduPCS.tex', 'BaiduPCS Documentation',
   'mozillazg', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'baidupcs', 'BaiduPCS Documentation',
     ['mozillazg'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'BaiduPCS', 'BaiduPCS Documentation',
   'mozillazg', 'BaiduPCS', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = 'BaiduPCS'
epub_author = 'mozillazg'
epub_publisher = 'mozillazg'
epub_copyright = '2013, mozillazg'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
#epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

# Fix unsupported image types using the PIL.
#epub_fix_images = False

# Scale large images.
#epub_max_image_width = 0

# If 'no', URL addresses will not be shown.
#epub_show_urls = 'inline'

# If false, no index is generated.
#epub_use_index = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = test_pcs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
# from StringIO import StringIO
import time
# from PIL import Image

from baidupcs import PCS, InvalidToken
from .utils import content_md5, content_crc32, slice_md5

access_token = '23.a4c9142268c190e82bff02905fb79b98.2592000.1397954722.570579779-1274287'
pcs = PCS(access_token)

verify = True
# verify = False  # 因为在我电脑上会出现 SSLError 所以禁用 https 证书验证


def _file(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(current_dir, filename)
    f = open(filepath, 'rb')  # rb 模式
    return f


def test_invalidtoken():
    try:
        PCS('abc').info()
    except InvalidToken:
        assert True
    else:
        assert False


def test_info():
    """磁盘配额信息"""
    response = pcs.info()
    assert response.ok and response.json()


def test_upload():
    """上传"""
    response = pcs.upload('/apps/test_sdk/test.txt', _file('test1'),
                          ondup='overwrite', verify=verify)
    assert response.ok and response.json()

    response = pcs.upload('/apps/test_sdk/test.txt', _file('test1'),
                          ondup='overwrite', verify=verify,
                          headers={'Accept': '*/*'})
    assert response.ok and response.json()


def test_upload_tmpfile():
    """分片上传 - 上传临时文件"""
    response = pcs.upload_tmpfile(_file('test1'), verify=verify)
    assert response.ok and response.json()


def test_upload_superfile():
    f1_md5 = pcs.upload_tmpfile(_file('test1'), verify=verify).json()['md5']
    f2_md5 = pcs.upload_tmpfile(_file('test2'), verify=verify).json()['md5']
    time.sleep(1)
    response = pcs.upload_superfile('/apps/test_sdk/super2.txt',
                                    [f1_md5, f2_md5], ondup='overwrite')
    assert response.ok and response.json()


def test_download():
    response = pcs.download('/apps/test_sdk/super2.txt', verify=verify)
    assert response.ok and 'abc'.encode() in response.content


def test_download_range():
    test_upload_superfile()
    headers = {'Range': 'bytes=0-2'}
    response1 = pcs.download('/apps/test_sdk/super2.txt', headers=headers,
                             verify=verify)
    assert response1.content == 'abc'.encode()
    headers = {'Range': 'bytes=3-5'}
    response2 = pcs.download('/apps/test_sdk/super2.txt', headers=headers,
                             verify=verify)
    assert response2.content == 'def'.encode()


def test_mkdir():
    response = pcs.mkdir('/apps/test_sdk/testmkdir')
    assert response.json()
    if not response.ok:
        assert response.json()['error_code'] == 31061


def test_meta():
    response = pcs.meta('/apps/test_sdk/super2.txt')
    assert response.ok and response.json()


def test_multi_meta():
    response = pcs.multi_meta(['/apps/test_sdk/super2.txt',
                              '/apps/test_sdk/testmkdir'])
    assert response.ok and response.json()


def test_list_files():
    response = pcs.list_files('/apps/test_sdk/testmkdir')
    assert response.ok and response.json()


def test_move():
    response = pcs.move('/apps/test_sdk/test.txt',
                        '/apps/test_sdk/testmkdir/a.txt')
    assert response.json()
    if not response.ok:
        assert response.json()['error_code'] == 31061


def test_multi_move():
    pcs.upload('/apps/test_sdk/test.txt', _file('test1'), verify=verify)
    pcs.upload('/apps/test_sdk/b.txt', _file('test1'), verify=verify)
    path_list = [
        ('/apps/test_sdk/test.txt', '/apps/test_sdk/testmkdir/b.txt'),
        ('/apps/test_sdk/b.txt', '/apps/test_sdk/testmkdir/a.txt'),
    ]
    time.sleep(1)
    response = pcs.multi_move(path_list)
    if not response.ok:
        assert response.json()['error_code'] == 31061


def test_copy():
    pcs.upload('/apps/test_sdk/test.txt', _file('test1'), verify=verify)
    response = pcs.copy('/apps/test_sdk/test.txt',
                        '/apps/test_sdk/testmkdir/c.txt')
    if not response.ok:
        assert response.json()['error_code'] == 31061


def test_multi_copy():
    pcs.upload('/apps/test_sdk/test.txt', _file('test1'), verify=verify)
    pcs.upload('/apps/test_sdk/b.txt', _file('test2'), verify=verify)
    path_list = [
        ('/apps/test_sdk/test.txt', '/apps/test_sdk/testmkdir/b.txt'),
        ('/apps/test_sdk/b.txt', '/apps/test_sdk/testmkdir/a.txt'),
    ]
    time.sleep(1)
    response = pcs.multi_copy(path_list)
    if not response.ok:
        assert response.json()['error_code'] == 31061


def test_delete():
    pcs.upload('/apps/test_sdk/testmkdir/e.txt', _file('test3'), verify=verify)
    time.sleep(1)
    response = pcs.delete('/apps/test_sdk/testmkdir/e.txt')
    assert response.ok


def test_multi_delete():
    pcs.upload('/apps/test_sdk/testmkdir/e.txt', _file('test1'), verify=verify)
    pcs.upload('/apps/test_sdk/testmkdir/d.txt', _file('test2'), verify=verify)
    time.sleep(1)
    response = pcs.multi_delete(['/apps/test_sdk/testmkdir/e.txt',
                                '/apps/test_sdk/testmkdir/d.txt'])
    assert response.ok


def test_search():
    response = pcs.upload('/apps/test_sdk/test.txt', _file('test1'),
                          ondup='overwrite', verify=verify)
    response = pcs.search('/apps/test_sdk/', 'test')
    assert response.ok


def test_thumbnail():
    response = pcs.thumbnail('/apps/test_sdk/testmkdir/404.png', 100, 100)
    # im = Image.open(StringIO(response.content))
    # im.show()
    assert response.ok


def test_diff():
    pcs.upload('/apps/test_sdk/testmkdir/h.txt', _file('test2'),
               ondup='overwrite', verify=verify)
    response0 = pcs.diff()
    new_cursor = response0.json()['cursor']

    time.sleep(1)
    pcs.upload('/apps/test_sdk/testmkdir/h.txt', str(time.time()),
               ondup='overwrite', verify=verify)
    response1 = pcs.diff(cursor=new_cursor)
    new_cursor = response1.json()['cursor']

    time.sleep(1)
    pcs.upload('/apps/test_sdk/testmkdir/h.txt', str(time.time()),
               ondup='overwrite', verify=verify)
    response2 = pcs.diff(cursor=new_cursor)
    assert response2.ok and response2.json()


def test_video_convert():
    response = pcs.video_convert('/apps/test_sdk/testmkdir/test.mp4',
                                 'M3U8_320_240')
    assert response.ok


def test_list_streams():
    response1 = pcs.list_streams('image')
    response2 = pcs.list_streams('doc', filter_path='/apps/test_sdk/test')
    assert response2.ok


def test_download_stream():
    response = pcs.download_stream('/apps/test_sdk/testmkdir/404.png',
                                   verify=verify)
    assert response.ok


def test_rapid_upload():
    content = ('a' * 1024 * 1024).encode('utf8')
    pcs.upload('/apps/test_sdk/testmkdir/upload.txt', content,
               ondup='overwrite', verify=verify)
    time.sleep(1)
    response = pcs.rapid_upload('/apps/test_sdk/testmkdir/rapid.txt',
                                len(content), content_md5(content),
                                content_crc32(content),
                                slice_md5(content[:1024 * 256]),
                                ondup='overwrite')
    assert response.ok


def test_add_download_task():
    url = 'http://img3.douban.com/pics/nav/logo_db.png'
    remote_path = '/apps/test_sdk/testmkdir/bdlogo.gif'
    response = pcs.add_download_task(url, remote_path)
    assert response.ok


def test_query_download_tasks():
    url1 = 'http://img3.douban.com/pics/nav/lg_main_a11_1.png'
    url2 = 'http://img3.douban.com/pics/nav/logo_db.png'
    remote_path = '/apps/test_sdk/testmkdir/%s'
    task1 = pcs.add_download_task(url1, remote_path % os.path.basename(url1))
    task2 = pcs.add_download_task(url2, remote_path % os.path.basename(url2))

    time.sleep(1)
    task_ids = [task1.json()['task_id'], task2.json()['task_id']]
    response = pcs.query_download_tasks(task_ids)
    assert response.ok


def test_list_download_tasks():
    response = pcs.list_download_tasks()
    assert response.ok


def test_cancel_download_task():
    response = pcs.list_download_tasks()
    task_info = response.json()['task_info']
    if task_info:
        task_id = task_info[0]['task_id']
        response2 = pcs.cancel_download_task(task_id)
        assert response2.ok


def test_list_recycle_bin():
    pcs.upload('/apps/test_sdk/testmkdir/10.txt', _file('test2'),
               ondup='overwrite', verify=verify)
    time.sleep(1)
    pcs.delete('/apps/test_sdk/testmkdir/10.txt')
    time.sleep(1)
    response = pcs.list_recycle_bin()
    assert response.ok


def test_restore_recycle_bin():
    pcs.upload('/apps/test_sdk/testmkdir/10.txt', _file('test1'),
               ondup='overwrite', verify=verify)
    pcs.delete('/apps/test_sdk/testmkdir/10.txt')

    time.sleep(1)
    response1 = pcs.list_recycle_bin()
    fs_id = response1.json()['list'][0]['fs_id']
    response = pcs.restore_recycle_bin(fs_id)
    assert response.ok


def test_multi_restore_recycle_bin():
    pcs.upload('/apps/test_sdk/testmkdir/1.txt', _file('test2'),
               ondup='overwrite', verify=verify)
    time.sleep(1)
    pcs.delete('/apps/test_sdk/testmkdir/1.txt')
    pcs.upload('/apps/test_sdk/testmkdir/2.txt', _file('test1'),
               ondup='overwrite', verify=verify)

    time.sleep(1)
    pcs.delete('/apps/test_sdk/testmkdir/2.txt')
    time.sleep(1)
    response1 = pcs.list_recycle_bin()
    fs_ids = [x['fs_id'] for x in response1.json()['list'][:1]]
    response = pcs.multi_restore_recycle_bin(fs_ids)
    assert response.ok


def test_clean_recycle_bin():
    response = pcs.clean_recycle_bin()
    assert response.ok

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from hashlib import md5
from zlib import crc32


def content_md5(content):
    """待秒传的文件的MD5."""
    return md5(content).hexdigest()


def content_crc32(content):
    """待秒传文件CRC32."""
    return '%x' % (crc32(content, 0) & 0xffffffff)


def slice_md5(content):
    """待秒传文件校验段的MD5."""
    return md5(content[:1024 * 256]).hexdigest()

########NEW FILE########
