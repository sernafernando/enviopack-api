from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import uvicorn
import os
from lxml import etree
import xml.sax
import requests
import html
import json
import pandas as pd
import re
from io import BytesIO

app = FastAPI()

# CORS libre
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


pusername = os.environ.get('PUSERNAME')
ppassword = os.environ.get('PPASWORD')
pcompany = os.environ.get('PCOMPANY')
pwebwervice = os.environ.get('PWEBWERVICE')
url_ws = os.environ.get('URL_WS')

token = None
consulta_resultados = []
token_actual = None
pedidos_guardados = []


def authenticate():
    
    soap_action = "http://microsoft.com/webservices/AuthenticateUser"
    xml_payload = f'<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Header><wsBasicQueryHeader xmlns="http://microsoft.com/webservices/"><pUsername>{pusername}</pUsername><pPassword>{ppassword}</pPassword><pCompany>{pcompany}</pCompany><pBranch>1</pBranch><pLanguage>2</pLanguage><pWebWervice>{pwebwervice}</pWebWervice></wsBasicQueryHeader></soap:Header><soap:Body><AuthenticateUser xmlns="http://microsoft.com/webservices/" /></soap:Body></soap:Envelope>'
    header_ws =  {"Content-Type": "text/xml", "SOAPAction": soap_action, "muteHttpExceptions": "true"}
    response = requests.post(url_ws, data=xml_payload,headers=header_ws)
    # Parsear la respuesta XML (suponiendo que response.content tiene el XML)
    root = etree.fromstring(response.content)

    # Definir los espacios de nombres para usarlos en las consultas XPath
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'microsoft': 'http://microsoft.com/webservices/'
    }


    # Busca el nodo AuthenticateUserResponse dentro del body
    # Buscar el contenido dentro de AuthenticateUserResult usando XPath
    auth_result = root.xpath('//microsoft:AuthenticateUserResult', namespaces=namespaces)

    # Mostrar el contenido si existe
    if auth_result:
        global token
        token = auth_result[0].text
    else:
        print("No se encontró el elemento AuthenticateUserResult") # Muestra el contenido del nodo si lo tiene
    
    return token
class LargeXMLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.result_content = []
        self.is_in_result = False

    def startElement(self, name, attrs):
        # Cuando el parser encuentra el inicio de un elemento
        if name == 'wsGBPScriptExecute4DatasetResult':
            self.is_in_result = True

    def endElement(self, name):
        # Cuando el parser encuentra el final de un elemento
        if name == 'wsGBPScriptExecute4DatasetResult':
            self.is_in_result = False

    def characters(self, content):
        # Al encontrar contenido de texto dentro de un nodo
        if self.is_in_result:
            self.result_content.append(content)

def ventas_por_fuera(mlID: str, token: str):
    xml_payload = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Header>
        <wsBasicQueryHeader xmlns="http://microsoft.com/webservices/">
            <pUsername>{pusername}</pUsername>
            <pPassword>{ppassword}</pPassword>
            <pCompany>{pcompany}</pCompany>
            <pWebWervice>{pwebwervice}</pWebWervice>
            <pAuthenticatedToken>{token}</pAuthenticatedToken>
        </wsBasicQueryHeader>
    </soap:Header>
    <soap:Body>
        <wsGBPScriptExecute4Dataset xmlns="http://microsoft.com/webservices/">
            <strScriptLabel>mlidToSheets</strScriptLabel>
            <strJSonParameters>{{"mlID": "{mlID}"}}</strJSonParameters>
        </wsGBPScriptExecute4Dataset>
    </soap:Body>
    </soap:Envelope>'''

    headers = {"Content-Type": "text/xml"}
    response = requests.post(url_ws, data=xml_payload.encode('utf-8'), headers=headers)

    if response.status_code != 200:
        return None

    # XML Parsing
    parser = xml.sax.make_parser()
    handler = LargeXMLHandler()
    parser.setContentHandler(handler)
    xml.sax.parseString(response.content, handler)

    result_content = ''.join(handler.result_content)
    unescaped_result = html.unescape(result_content)
    match = re.search(r'\[.*?\]', unescaped_result)

    if not match:
        return None

    try:
        data = json.loads(match.group(0))
        return pd.DataFrame(data)
    except Exception:
        return None

@app.get("/", response_class=HTMLResponse)
def form():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Extraer Pedidos</title>
    <link rel="icon" type="image/png" href="https://descargas.gaussonline.com.ar/favicon%20white.png">
    <style>
        body {
            background-color: #121212;
            color: #f1f1f1;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            max-width: 600px;
            width: 100%;
            background-color: #1e1e1e;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 0 12px rgba(0,0,0,0.5);
        }
        h1 {
            margin-bottom: 1.5rem;
            text-align: center;
        }
        input[type="file"] {
            background-color: #333;
            border: none;
            padding: 0.5rem;
            color: white;
            margin-bottom: 1rem;
            width: 100%;
        }
        button {
            background-color: #00b894;
            color: white;
            border: none;
            padding: 0.7rem 1.2rem;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 1rem;
            width: 100%;
            font-size: 1rem;
        }
        button:hover {
            background-color: #019874;
        }
        .logo {
            margin-bottom: 1.5rem;
            text-align: center;
        }
        .logo img {
            max-width: 200px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="https://mshop.gaussonline.com.ar/Logo%20%2B%20web%20blanco.png" alt="Logo Gaussonline">
        </div>
        <h1>Subí tu archivo PDF</h1>
        <form action="/extract" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required />
            <button type="submit">Procesar</button>
        </form>
    </div>
</body>
</html>
"""

@app.post("/extract", response_class=HTMLResponse)
async def extract(file: UploadFile = File(...)):
    pedidos = []
    

    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    if 'PEDIDO:' in line.upper():
                        parts = line.upper().split("PEDIDO:")
                        if len(parts) > 1:
                            numero = parts[1].strip().split()[0]
                            pedidos.append(numero)

    pedidos_str = "".join(f"<li>{p}</li>" for p in pedidos)
    pedidos_txt = "\\n".join(pedidos)

    global pedidos_guardados
    pedidos_guardados = pedidos.copy()
    print(f"Pedidos a consultar: {pedidos_guardados}")

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Pedidos encontrados</title>
    <link rel="icon" type="image/png" href="https://descargas.gaussonline.com.ar/favicon%20white.png">
    <style>
        body {{
            background-color: #121212;
            color: #f1f1f1;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{
            max-width: 600px;
            width: 100%;
            background-color: #1e1e1e;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 0 12px rgba(0,0,0,0.5);
        }}
        h1 {{
            margin-bottom: 1.5rem;
            text-align: center;
        }}
        ul {{
            list-style: none;
            padding: 0;
            margin-bottom: 2rem;
            text-align: center;
        }}
        li {{
            background-color: #2c2c2c;
            margin: 0.3rem 0;
            padding: 0.5rem;
            border-radius: 8px;
        }}
        .buttons {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        button {{
            background-color: #00b894;
            color: white;
            border: none;
            padding: 0.7rem 1.2rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
        }}
        button:hover {{
            background-color: #019874;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📦 Pedidos encontrados</h1>
        <ul>{pedidos_str}</ul>
        <div class="buttons">
            <button onclick="copiar()">Copiar al portapapeles</button>
            <button onclick="descargar()">Descargar como .txt</button>
            <button onclick="window.location.href='/consulta-completa'">Generar consulta</button>
        </div>
    </div>
    <script>
        const pedidos = `{pedidos_txt}`.split("\\n");

        function copiar() {{
            navigator.clipboard.writeText(pedidos.join('\\n'))
                .then(() => alert('Copiado al portapapeles'))
                .catch(err => alert('Error al copiar'));
        }}

        function descargar() {{
            const blob = new Blob([pedidos.join('\\n')], {{ type: 'text/plain' }});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'pedidos.txt';
            link.click();
        }}
    </script>
</body>
</html>
"""

@app.api_route("/ping", methods=["HEAD", "GET"], response_class=PlainTextResponse)
async def ping(request: Request):
    return "pong"

@app.get("/consulta-completa", response_class=HTMLResponse)
async def consulta_completa():
    global token_actual

    # Asegurarse de tener token válido
    if not token_actual:
        token_actual = authenticate()

    tablas_html = []
    print(f"Token actual: {token_actual}")

    for pedido in pedidos_guardados:
        print(f"Consultando pedido: {pedido}")
        try:
            df = ventas_por_fuera(mlID=pedido, token=token_actual)
        except Exception as e:
            print(f"Error al consultar pedido {pedido}: {e}")


        if df is None or df.empty:
            # Reintento automático si falla
            token_actual = authenticate()
            try:
                df = ventas_por_fuera(mlID=pedido, token=token_actual)
            except Exception as e:
                print(f"Error al consultar pedido {pedido}: {e}")
        
        if df is not None and not df.empty:
            tabla = df.to_html(classes="table", index=False)
            consulta_resultados[pedido] = df
        else:
            tabla = f"<p>No se encontró información para pedido {pedido}</p>"

        tablas_html.append(f"<h3>Pedido: {pedido}</h3>{tabla}")

    html = f"""
    <html>
    <head>
        <style>
            body {{
                background-color: #121212;
                color: white;
                font-family: sans-serif;
                padding: 2rem;
            }}
            .table {{
                background-color: #1e1e1e;
                border-collapse: collapse;
                width: 100%;
                color: white;
            }}
            .table th, .table td {{
                border: 1px solid #333;
                padding: 8px;
                text-align: left;
            }}
            .table th {{
                background-color: #00b894;
            }}
            h3 {{
                margin-top: 2rem;
                border-bottom: 1px solid #00b894;
            }}
        </style>
    </head>
    <body>
        <h1>Resultados por Pedido</h1>
        {''.join(tablas_html)}
    </body>
    </html>
    """

       


    return HTMLResponse(content=html)

@app.get("/export-excel")
def exportar_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for pedido, df in consulta_resultados.items():
            df.to_excel(writer, sheet_name=str(pedido)[:31], index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=consulta_pedidos.xlsx"})

@app.get("/pedidos-json")
def pedidos_en_json():
    salida = {}
    for pedido, df in consulta_resultados.items():
        salida[pedido] = df.to_dict(orient="records")
    return JSONResponse(content=salida)