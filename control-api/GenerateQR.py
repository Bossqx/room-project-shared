"""
GenerateQR.py

Generates a QR code image for a given URL and saves it as a PNG next to
this script.

Usage:
    python GenerateQR.py
"""

import qrcode

URL = "https://cos.nrru.ac.th/SSNM/"
OUTPUT_PATH = "SSNM_qr.png"


def generate_qr(url: str, output_path: str) -> None:
    qr = qrcode.QRCode(
        version=None,  # auto-size to fit the data
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    print(f"QR code for {url} saved to {output_path}")


if __name__ == "__main__":
    generate_qr(URL, OUTPUT_PATH)
