import subprocess
import time
import json
import os
import hashlib
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode
import pyotp
from urllib.parse import urlparse, parse_qs, unquote, quote, urlencode
from pathlib import Path
import config.data as data

OTP_DIGESTS = {
    "SHA1": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA512": hashlib.sha512,
}

MICROSOFT_AUTHENTICATOR_HOST = "login.microsoftonline.com"
MICROSOFT_AUTHENTICATOR_PATH = "/authenticatorApp/activateAccount"

def get_otp_file_path():
    """Retorna o caminho para o arquivo de OTPs no diretório cache"""
    cache_dir = Path(data.CACHE_DIR) / "otp"
    # Cria o diretório se não existir
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = cache_dir / "otp_codes.json"
    
    # Cria o arquivo se não existir
    if not file_path.exists():
        with open(file_path, 'w') as f:
            json.dump([], f)
        print(f"Arquivo {file_path} criado com sucesso!")
    
    return file_path

def capture_selected_area(filename="/tmp/screenshot.png"):
    """
    Usa o slop para permitir que o usuário selecione a área da tela e,
    em seguida, captura essa área com o maim.
    """
    # Executa o slop para capturar as coordenadas interativamente.
    # A opção -f define o formato de saída: x, y, largura e altura.
    try:
        result = subprocess.run(
            ["slop", "-t", "0", "-f", "%x %y %w %h"],
            check=True,
            capture_output=True,
            text=True
        )
        coords = result.stdout.strip().split()
        if len(coords) != 4:
            print("Coordenadas inválidas obtidas pelo slop.")
            return None
        x, y, w, h = coords
    except subprocess.CalledProcessError as e:
        print("Erro ao selecionar a área com slop:", e)
        return None
    # Usa o maim para capturar a área selecionada com base nas coordenadas obtidas.
    try:
        subprocess.run(
            ["maim", "-g", f"{w}x{h}+{x}+{y}", filename],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Erro ao capturar screenshot com maim:", e)
        return None
    return filename

def _query_value(query, key, default=None):
    return query.get(key, [default])[0]

def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def parse_otpauth_uri(uri):
    parsed = urlparse(uri.strip())
    if parsed.scheme.lower() != "otpauth" or parsed.netloc.lower() != "totp":
        return None

    query = parse_qs(parsed.query)
    secret = _query_value(query, "secret")
    if not secret:
        return None

    label = unquote(parsed.path.lstrip("/")) if parsed.path else ""
    account_name = label
    issuer_from_path = None

    if ":" in label:
        issuer_from_path, account_name = label.split(":", 1)
        account_name = account_name.lstrip()

    issuer_from_query = _query_value(query, "issuer")
    issuer = issuer_from_path or issuer_from_query or account_name or "OTP"
    period = _parse_int(_query_value(query, "period", "30"), 30)
    digits = _parse_int(_query_value(query, "digits", "6"), 6)
    algorithm = (_query_value(query, "algorithm", "SHA1") or "SHA1").upper()

    return {
        "secret": secret.replace(" ", "").upper(),
        "issuer": issuer,
        "account_name": account_name,
        "period": period,
        "digits": digits,
        "algorithm": algorithm,
    }

def is_microsoft_authenticator_activation_uri(uri):
    parsed = urlparse(uri.strip())
    return (
        parsed.netloc.lower() == MICROSOFT_AUTHENTICATOR_HOST
        and parsed.path == MICROSOFT_AUTHENTICATOR_PATH
    )

def build_totp(uri):
    otp_data = parse_otpauth_uri(uri)
    if otp_data is None:
        return None

    digest = OTP_DIGESTS.get(otp_data["algorithm"], hashlib.sha1)
    return pyotp.TOTP(
        otp_data["secret"],
        digits=otp_data["digits"],
        interval=otp_data["period"],
        digest=digest,
    )

def create_otpauth_uri(secret, issuer="OTP", account_name="", period=30, digits=6, algorithm="SHA1"):
    secret = secret.replace(" ", "").replace("-", "").upper()
    issuer = issuer.strip() or "OTP"
    account_name = account_name.strip()
    algorithm = (algorithm or "SHA1").upper()
    period = _parse_int(period, 30)
    digits = _parse_int(digits, 6)

    label = f"{issuer}:{account_name}" if account_name else issuer
    query = urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": algorithm,
        "digits": digits,
        "period": period,
    })

    return f"otpauth://totp/{quote(label, safe='')}?{query}"

def create_otp_entry(secret, issuer="OTP", account_name="", period=30, digits=6, algorithm="SHA1"):
    uri = create_otpauth_uri(secret, issuer, account_name, period, digits, algorithm)
    return create_otp_entry_from_uri(uri)

def create_otp_entry_from_uri(uri):
    otp_data = parse_otpauth_uri(uri)
    totp = build_totp(uri)

    if otp_data is None or totp is None:
        return None

    # Force generation once so invalid manual secrets fail before being saved.
    totp.now()

    return {
        "timestamp": datetime.now().isoformat(),
        "qr_data": uri,
        "type": "otp",
        **otp_data,
    }

def read_and_save_to_json():
    # Obter o caminho completo para o arquivo JSON
    json_file = get_otp_file_path()
    
    screenshot = capture_selected_area()
    if screenshot is None:
        print("Falha ao capturar a área selecionada.")
        return False
    
    # Pequena pausa para garantir que o arquivo foi salvo
    time.sleep(1)
    
    # Abre a imagem capturada
    try:
        img = Image.open(screenshot)
    except Exception as e:
        print("Erro ao abrir a imagem:", e)
        return False
    
    # Decodifica QR Code(s) na imagem
    decoded_objects = decode(img)
    if not decoded_objects:
        print("Nenhum QR Code detectado na área selecionada.")
        return False
    
    results = []
    
    for obj in decoded_objects:
        data = obj.data.decode("utf-8")
        print("QR Code detectado:", data)
        
        result_entry = {
            "timestamp": datetime.now().isoformat(),
            "qr_data": data
        }
        
        otp_data = parse_otpauth_uri(data)

        if otp_data:
            totp = build_totp(data)
            if totp is None:
                print("Não foi possível gerar o OTP a partir da URI detectada.")
                return False

            current_otp = totp.now()
            print(f"Código OTP gerado: {current_otp} (válido por {otp_data['period']} segundos)")
            
            result_entry.update({
                "type": "otp",
                **otp_data,
            })
        else:
            result_entry["type"] = "unknown"
            if is_microsoft_authenticator_activation_uri(data):
                print(
                    "Este QR é de ativação do Microsoft Authenticator e não contém "
                    "um segredo TOTP. No Azure, escolha a opção de configurar outro "
                    "aplicativo autenticador para obter um QR otpauth:// ou a chave "
                    "manual."
                )
            else:
                print("Formato não reconhecido. Esperava uma URI no formato otpauth://")
            return False
        
        results.append(result_entry)
    
    # Carregar dados existentes se o arquivo já existir
    existing_data = []
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Erro ao ler o arquivo {json_file}. Criando um novo.")
    
    # Adicionar novos resultados
    existing_data.extend(results)
    
    # Salvar no arquivo JSON
    with open(json_file, 'w') as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Dados OTP salvos em {json_file}")
    return True

def CodeOTP(uri):
    totp = build_totp(uri)
    if totp is None:
        return None

    try:
        return totp.now()
    except Exception as error:
        print(f"Erro ao gerar OTP: {error}")
        return None