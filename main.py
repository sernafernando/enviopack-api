from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from PyPDF2 import PdfReader
import uvicorn

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def form():
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
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required />
            <button type="submit">Procesar</button>
        </form>
    </div>
</body>
</html>
"""

@app.post("/upload", response_class=HTMLResponse)
async def upload(file: UploadFile = File(...)):
    reader = PdfReader(file.file)
    pedidos = []

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.splitlines():
            try:
                pedido = line.split("PEDIDO:")[1].strip().split()[0]
                pedidos.append(pedido)
            except IndexError:
                continue 

    joined = "\\n".join(pedidos)
    return f"""
    <h2>Pedidos encontrados:</h2>
    <textarea rows='10' cols='60' id='output'>{joined}</textarea><br>
    <button onclick="navigator.clipboard.writeText(document.getElementById('output').value)">Copiar</button>
    <a href="data:text/plain;charset=utf-8,{joined}" download="pedidos.txt">
        <button>Descargar TXT</button>
    </a>
    """
