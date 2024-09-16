from pyzbar.pyzbar import decode
from PIL import Image
from uuid import uuid4
import base64
import os
import time
import json
import pronotepy
import requests
from io import BytesIO


def connection_with_qr_code(file_url,
                            verif_code: str = "0000"
                            ) -> pronotepy.Client | str:
    try:
        response = requests.get(file_url)
        image = Image.open(BytesIO(response.content))
    except Exception as e:
        if str(e) == f"[Errno 2] No such file or directory: '{file_url}'":
            error = f"Pas de fichier sous le nom de '{file_url}'"
            return error
        return ""

    decoded_objects = decode(image)

    try:
        qrcode_data = json.loads(decoded_objects[0].data.decode("utf-8"))
    except Exception as e:
        return f"Can not decode QR code: {str(e)}"

    pin = verif_code
    uuid = uuid4()

    try:
        client = pronotepy.Client.qrcode_login(qrcode_data, pin, str(uuid))
    except Exception as e:
        if str(e) == "invalid confirmation code":
            error = "Mauvais mot de passe"
        elif str(
                e
        ) == "('Decryption failed while trying to un pad. (probably bad decryption key/iv)', 'exception happened during login -> probably the qr code has expired (qr code is valid during 10 minutes)')":
            error = "le QR code à éxpiré"
        else:
            error = e
        return f"N'arrive pas a se connecter au QR code: {str(error)}"

    return client


# client = connection_with_qr_code("download.png","1234")
# if isinstance(client, str):
#     print(client)
# else:
#     print(client.discussions(False))
