from datetime import datetime
from pathlib import Path

import qrcode


def create_access_code(passport_series_and_number: str) -> str:
    """Return access code."""
    access_code = (
        f'{passport_series_and_number}'
        f'{int(datetime.now().timestamp())}'
    )
    return access_code


def create_qrcode(code: str) -> str:
    """Create QR-code image and return it's path."""
    qrcode_image = qrcode.make(code)
    qrcodes_directory = './qrcodes/'
    Path(qrcodes_directory).mkdir(exist_ok=True)
    qrcode_image_path = (
        f'{qrcodes_directory}/qr{int(datetime.now().timestamp())}.jpg'
    )
    qrcode_image.save(qrcode_image_path)
    return qrcode_image_path
