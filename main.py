from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from PyPDF2 import PdfReader
import uvicorn

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def form():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Extraer Pedidos</title>
    </head>
    <body>
        <h1>Subí tu PDF</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" />
            <button type="submit">Subir</button>
        </form>
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
            if "PEDIDO:" in line:
                pedido = line.split("PEDIDO:")[-1].strip().split()[0]
                pedidos.append(pedido)

    joined = "\\n".join(pedidos)
    return f"""
    <h2>Pedidos encontrados:</h2>
    <textarea rows='10' cols='60' id='output'>{joined}</textarea><br>
    <button onclick="navigator.clipboard.writeText(document.getElementById('output').value)">Copiar</button>
    <a href="data:text/plain;charset=utf-8,{joined}" download="pedidos.txt">
        <button>Descargar TXT</button>
    </a>
    """
