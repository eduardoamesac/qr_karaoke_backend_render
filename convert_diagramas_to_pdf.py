#!/usr/bin/env python3
"""
Script para convertir DIAGRAMAS_CREDITOS.md a PDF
"""

import os
import sys
from pathlib import Path

# Intentar importar las librerías necesarias
try:
    from markdown2 import markdown
    from xhtml2pdf import pisa
except ImportError:
    print("📦 Instalando dependencias requeridas...")
    os.system('pip install markdown2 xhtml2pdf pillow')
    from markdown2 import markdown
    from xhtml2pdf import pisa

# Rutas
script_dir = os.path.dirname(os.path.abspath(__file__))
md_file = os.path.join(script_dir, 'DIAGRAMAS_CREDITOS.md')
pdf_file = os.path.join(script_dir, 'DIAGRAMAS_CREDITOS.pdf')

print("="*60)
print("CONVERTIDOR: DIAGRAMAS_CREDITOS.md → PDF")
print("="*60)

# Verificar que el archivo existe
if not os.path.exists(md_file):
    print(f"❌ Error: {md_file} no encontrado")
    sys.exit(1)

# Leer el archivo markdown
print(f"\n📄 Leyendo archivo: {md_file}")
with open(md_file, 'r', encoding='utf-8') as f:
    md_content = f.read()

# Convertir markdown a HTML
print("🔄 Convirtiendo Markdown a HTML...")
html_content = markdown(md_content, extras=['fenced-code-blocks', 'tables'])

# Crear HTML completo con estilos optimizados para PDF
html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Courier New', 'Courier', monospace;
            line-height: 1.5;
            color: #333;
            background-color: white;
            padding: 20px;
            font-size: 11pt;
        }}
        
        h1 {{
            font-size: 20pt;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin: 20px 0 15px 0;
            page-break-after: avoid;
        }}
        
        h2 {{
            font-size: 16pt;
            color: #34495e;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
            margin: 15px 0 10px 0;
            page-break-after: avoid;
        }}
        
        h3 {{
            font-size: 13pt;
            color: #555;
            margin: 12px 0 8px 0;
            page-break-after: avoid;
        }}
        
        p {{
            margin-bottom: 10px;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            color: #d63384;
        }}
        
        pre {{
            background-color: #f4f4f4;
            border-left: 4px solid #3498db;
            padding: 12px;
            overflow-x: auto;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 10pt;
            white-space: pre-wrap;
            word-wrap: break-word;
            page-break-inside: avoid;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            page-break-inside: avoid;
        }}
        
        th, td {{
            border: 1px solid #bdc3c7;
            padding: 10px;
            text-align: left;
            font-size: 10pt;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        
        tr:nth-child(even) {{
            background-color: #ecf0f1;
        }}
        
        tr:hover {{
            background-color: #d5dbdb;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        ul, ol {{
            margin-left: 20px;
            margin-bottom: 10px;
        }}
        
        li {{
            margin-bottom: 5px;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin: 10px 0;
            color: #555;
        }}
        
        .page-break {{
            page-break-after: always;
        }}
        
        /* Estilos para el contenido ASCII art */
        pre {{
            font-size: 9pt;
            letter-spacing: -0.5pt;
        }}
    </style>
</head>
<body>
    {html_content}
    
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
    <p style="text-align: center; color: #999; font-size: 9pt; margin-top: 20px;">
        Generado automáticamente el 04/02/2026 | Sistema de Créditos para Karaoke
    </p>
</body>
</html>
"""

# Convertir HTML a PDF
print(f"📝 Generando PDF: {pdf_file}")

with open(pdf_file, 'wb') as f:
    pisa_status = pisa.CreatePDF(
        html_doc,
        dest=f,
        encoding='UTF-8'
    )

if pisa_status.err:
    print(f"❌ Error al crear el PDF: {pisa_status.err}")
    sys.exit(1)
else:
    print(f"\n✅ PDF creado exitosamente!")
    print(f"📍 Ubicación: {os.path.abspath(pdf_file)}")
    
    # Mostrar tamaño del archivo
    size = os.path.getsize(pdf_file) / 1024  # En KB
    print(f"📊 Tamaño: {size:.2f} KB")
    
    print("\n✨ El archivo está listo para descargar/imprimir")
