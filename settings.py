EASYLIST_URL = "https://easylist.to/easylist/easylist.txt"

BLOCKING_SYMBOLS = ('-', '.', '/', ':', '?', '&', '_', "=")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif",
                    ".webp", ".avif", ".svg", ".ico",
                    ".apng", ".bmp", ".tiff", ".tif",
                    ".jfif", ".heif", ".heic")

TYPES = {
    "jpg": "image", "jpeg": "image", "png": "image", "gif": "image", "webp": "image", "avif": "image", "svg": "image",
    "ico": "image", "apng": "image", "bmp": "image", "tiff": "image", "tif": "image", "jfif": "image", "heif": "image",
    "heic": "image", "css": "stylesheet", "js": "script", "html": "document", "xml": "document", "json": "document",
    "pdf": "document", "doc": "document", "docx": "document", "xls": "document", "xlsx": "document", "ppt": "document",
    "pptx": "document", "mp4": "media", "mp3": "media", "avi": "media", "mov": "media", "wav": "media", "ogg": "media",
    "flac": "media", "mkv": "media", "webm": "media", "zip": "document", "rar": "document", "tar": "document", "woff": "font",
    "woff2": "font", "ttf": "font", "otf": "font", "eot": "font", "svgz": "font", "woff3": "font", "woff4": "font",

}

REQUEST_TYPES = ['stylesheet', 'image', 'script', 'object', 'xmlhttprequest', 'third-party', 'subdocument', 'ping',
                 'media', 'document', 'popup', 'rewrite']

DOWNLOADABLE_FORMATS = {'stylesheet': 'css', 'image': '', 'script': 'js', 'document': 'html'}

FORMAT_CONVERTER = {
    'stylesheet': ['css'], 'script': ['js'], 'document': ['html'], 'image': ['aces', 'apng', 'avci', 'avcs', 'avif', 'bmp', 'cgm', 'dicom-rle', 'dpx', 'emf', 'example', 'fits', 'g3fax', 'gif', 'heic', 'heic-sequence', 'heif', 'heif-sequence', 'hej2k', 'hsj2', 'ief', 'j2c', 'jaii', 'jais', 'jls', 'jp2', 'jpeg', 'jph', 'jphc', 'jpm', 'jpx', 'jxl', 'jxr', 'jxrA', 'jxrS', 'jxs', 'jxsc', 'jxsi', 'jxss', 'ktx', 'ktx2', 'naplps', 'png', 'prs.btif', 'prs.pti', 'pwg-raster', 'svg+xml', 't38', 'tiff', 'tiff-fx', 'vnd.adobe.photoshop', 'vnd.airzip.accelerator.azv', 'vnd.blockfact.facti', 'vnd.clip', 'vnd.cns.inf2', 'vnd.dece.graphic', 'vnd.djvu', 'vnd.dwg', 'vnd.dxf', 'vnd.dvb.subtitle', 'vnd.fastbidsheet', 'vnd.fpx', 'vnd.fst', 'vnd.fujixerox.edmics-mmr', 'vnd.fujixerox.edmics-rlc', 'vnd.globalgraphics.pgb', 'vnd.microsoft.icon', 'vnd.mix', 'vnd.ms-modi', 'vnd.mozilla.apng', 'vnd.net-fpx', 'vnd.pco.b16', 'vnd.radiance', 'vnd.sealed.png', 'vnd.sealedmedia.softseal.gif', 'vnd.sealedmedia.softseal.jpg', 'vnd.svf', 'vnd.tencent.tap', 'vnd.valve.source.texture', 'vnd.wap.wbmp', 'vnd.xiff', 'vnd.zbrush.pcx', 'webp', 'wmf', 'x-emf', 'x-wmf']

}

__all__ = [
    "EASYLIST_URL",
    "BLOCKING_SYMBOLS",
    "IMAGE_EXTENSIONS",
    "REQUEST_TYPES",
    "DOWNLOADABLE_FORMATS",
    "FORMAT_CONVERTER"
]
