# -*- coding: utf-8 -*-
"""
Genera un PDF que documenta la metodologia utilizada para traducir el documento
"3T Quick Start for cleaning" desde su PDF original al idioma destino.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem,
    Table, TableStyle, HRFlowable
)

AZUL = HexColor("#1F3864")
AZUL_CLARO = HexColor("#2E5496")
GRIS = HexColor("#595959")
GRIS_CLARO = HexColor("#F2F2F2")

ARCHIVO_SALIDA = "Metodologia_de_Traduccion.pdf"

styles = getSampleStyleSheet()

estilo_titulo = ParagraphStyle(
    "TituloPrincipal", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=22, leading=27,
    textColor=AZUL, spaceAfter=6, alignment=TA_CENTER,
)
estilo_subtitulo = ParagraphStyle(
    "Subtitulo", parent=styles["Normal"],
    fontName="Helvetica", fontSize=12, leading=16,
    textColor=GRIS, alignment=TA_CENTER, spaceAfter=4,
)
estilo_h2 = ParagraphStyle(
    "Seccion", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=14, leading=18,
    textColor=AZUL_CLARO, spaceBefore=16, spaceAfter=8,
)
estilo_cuerpo = ParagraphStyle(
    "Cuerpo", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10.5, leading=15,
    textColor=HexColor("#222222"), alignment=TA_JUSTIFY, spaceAfter=8,
)
estilo_lista = ParagraphStyle(
    "Lista", parent=estilo_cuerpo, spaceAfter=4,
)
estilo_paso_titulo = ParagraphStyle(
    "PasoTitulo", parent=styles["Normal"],
    fontName="Helvetica-Bold", fontSize=11, leading=15,
    textColor=AZUL, spaceAfter=2,
)
estilo_nota = ParagraphStyle(
    "Nota", parent=styles["Normal"],
    fontName="Helvetica-Oblique", fontSize=9.5, leading=13,
    textColor=GRIS,
)


def construir():
    doc = SimpleDocTemplate(
        ARCHIVO_SALIDA, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.0 * cm,
        title="Metodologia de Traduccion del Documento PDF",
        author="Equipo de Traduccion",
    )

    el = []

    # --- Portada / encabezado ---
    el.append(Paragraph("Metodologia de Traduccion", estilo_titulo))
    el.append(Paragraph(
        "Documento tecnico: descripcion del proceso aplicado para traducir "
        "el PDF conservando su formato y disposicion original",
        estilo_subtitulo,
    ))
    el.append(Spacer(1, 6))
    el.append(HRFlowable(width="100%", thickness=1.2, color=AZUL_CLARO))
    el.append(Spacer(1, 6))

    # Tabla de metadatos
    datos = [
        ["Documento original:", "3T Quick Start for cleaning (CP_IFU_16-XX-XX_Q_USA_001).pdf"],
        ["Tipo de documento:", "Instrucciones de uso / Guia rapida"],
        ["Fecha:", "08 de junio de 2026"],
        ["Objetivo:", "Traducir el contenido manteniendo el mismo diseno y ubicacion del texto"],
    ]
    tabla = Table(datos, colWidths=[4.2 * cm, 12.0 * cm])
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), AZUL),
        ("TEXTCOLOR", (1, 0), (1, -1), HexColor("#333333")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#D0D0D0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#FFFFFF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    el.append(tabla)
    el.append(Spacer(1, 14))

    # --- 1. Resumen ---
    el.append(Paragraph("1. Resumen general", estilo_h2))
    el.append(Paragraph(
        "El presente documento describe la metodologia empleada para traducir el "
        "archivo PDF original. El criterio principal fue preservar de manera fiel el "
        "diseno, la estructura y la posicion de cada elemento del documento. Para "
        "lograrlo, el proceso se dividio en tres etapas fundamentales: <b>(1) extraccion "
        "del texto</b>, <b>(2) traduccion individual de cada fragmento</b> y "
        "<b>(3) reinsercion del texto traducido en su ubicacion original</b>. De esta "
        "forma, el documento final conserva la misma apariencia que el original, pero "
        "con el contenido en el idioma destino.",
        estilo_cuerpo,
    ))

    # --- 2. Etapas del proceso ---
    el.append(Paragraph("2. Etapas del proceso", estilo_h2))

    pasos = [
        ("Paso 1 — Extraccion del texto",
         "Se solicito extraer todo el texto contenido en el PDF original. Cada "
         "fragmento de texto (titulos, parrafos, etiquetas, leyendas de imagenes, "
         "tablas y pies de pagina) se identifico junto con su posicion exacta dentro "
         "de la pagina. De esta manera se obtiene un inventario completo del contenido "
         "textual sin alterar todavia el documento."),
        ("Paso 2 — Traduccion individual de cada texto",
         "Cada fragmento extraido se tradujo por separado, de forma aislada del resto. "
         "Tratar cada texto de manera independiente permite controlar la calidad de la "
         "traduccion fragmento por fragmento, respetar la terminologia tecnica propia "
         "del documento y evitar mezclar o desplazar contenidos. El significado, el tono "
         "y la intencion del texto original se mantienen en la version traducida."),
        ("Paso 3 — Reinsercion en la misma ubicacion",
         "Una vez traducido, cada fragmento se volvio a colocar exactamente en el mismo "
         "lugar que ocupaba en el documento original. Se respetaron las coordenadas, el "
         "tamano del area de texto, el orden y la jerarquia visual. El resultado es un "
         "PDF traducido cuyo formato, maquetacion e imagenes permanecen identicos al "
         "original, cambiando unicamente el idioma del texto."),
    ]
    for titulo, texto in pasos:
        el.append(Paragraph(titulo, estilo_paso_titulo))
        el.append(Paragraph(texto, estilo_cuerpo))

    # --- 3. Flujo resumido ---
    el.append(Paragraph("3. Flujo de trabajo resumido", estilo_h2))
    flujo = [
        "Extraer cada texto del PDF original junto con su posicion.",
        "Traducir cada texto por separado al idioma destino.",
        "Reinsertar cada traduccion en el mismo lugar del documento.",
        "Verificar que el formato y la disposicion coincidan con el original.",
    ]
    el.append(ListFlowable(
        [ListItem(Paragraph(p, estilo_lista), leftIndent=6) for p in flujo],
        bulletType="1", bulletFontName="Helvetica-Bold",
        bulletColor=AZUL_CLARO, leftIndent=14,
    ))

    # --- 4. Beneficios ---
    el.append(Paragraph("4. Ventajas de esta metodologia", estilo_h2))
    ventajas = [
        "Conserva fielmente el diseno, las imagenes y la maquetacion del documento original.",
        "Permite controlar la calidad de cada fragmento de manera independiente.",
        "Mantiene la coherencia de la terminologia tecnica en todo el documento.",
        "Facilita la revision, ya que el texto traducido se ubica donde estaba el original.",
        "Reduce el riesgo de errores de desplazamiento u omision de contenido.",
    ]
    el.append(ListFlowable(
        [ListItem(Paragraph(v, estilo_lista), leftIndent=6) for v in ventajas],
        bulletType="bullet", bulletColor=AZUL_CLARO, leftIndent=14,
    ))

    el.append(Spacer(1, 16))
    el.append(HRFlowable(width="100%", thickness=0.8, color=HexColor("#CCCCCC")))
    el.append(Spacer(1, 4))
    el.append(Paragraph(
        "Documento generado automaticamente como registro de la metodologia de "
        "traduccion aplicada al PDF original.",
        estilo_nota,
    ))

    doc.build(el)
    print("PDF generado:", ARCHIVO_SALIDA)


if __name__ == "__main__":
    construir()
