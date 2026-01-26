# Guia de Desarrollo - Modulo Control Interno

## Manual para Programadores de Odoo 14 CE

Este documento proporciona la informacion tecnica necesaria para que otros programadores puedan crear modulos de Odoo 14 CE que se integren con el modulo `om_control_interno`.

---

## Tabla de Contenidos

1. [Informacion General del Modulo](#1-informacion-general-del-modulo)
2. [Dependencias](#2-dependencias)
3. [Modelos Principales](#3-modelos-principales)
4. [API Publica y Metodos de Integracion](#4-api-publica-y-metodos-de-integracion)
5. [Puntos de Extension](#5-puntos-de-extension)
6. [Ejemplos de Integracion](#6-ejemplos-de-integracion)
7. [Widgets JavaScript Personalizados](#7-widgets-javascript-personalizados)
8. [Constantes y Mapeos](#8-constantes-y-mapeos)
9. [Consideraciones de Rendimiento](#9-consideraciones-de-rendimiento)

---

## 1. Informacion General del Modulo

### Datos del Manifest

```python
{
    'name': 'Control Interno',
    'version': '1.0',
    'summary': 'Modulo para llevar un control interno de facturas',
    'depends': ['account', 'purchase'],
    'application': True,
}
```

### Estructura del Modulo

```
om_control_interno/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── control_interno_mensual.py    # Modelo principal
│   ├── costos_gastos_line.py         # Lineas de costos/gastos
│   ├── catalogo_cuentas.py           # Catalogo de cuentas contables
│   ├── factura_xml.py                # Facturas XML importadas
│   ├── purchase_order.py             # Extension de purchase.order
│   └── *_wizard.py                   # Asistentes varios
├── views/
├── security/
├── data/
└── static/src/js/
```

---

## 2. Dependencias

### Modulos Odoo Requeridos

| Modulo | Uso |
|--------|-----|
| `account` | Base contable, integracion con partidas |
| `purchase` | Ordenes de compra |

### Modelos de Odoo Utilizados

```python
# Modelos que este modulo utiliza y que pueden ser relevantes para integraciones
'res.partner'      # Proveedores
'res.country'      # Paises
'res.currency'     # Monedas
'purchase.order'   # Ordenes de compra (extendido con campo control_interno)
'ir.attachment'    # Archivos adjuntos (exportacion CSV)
```

### Dependencias Python

```python
from dateutil.relativedelta import relativedelta
import csv
import base64
import zipfile
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
import unicodedata
import io
```

---

## 3. Modelos Principales

### 3.1 control.interno.mensual

**Descripcion:** Modelo principal que agrupa el control de facturas y gastos por mes.

**Nombre Tecnico:** `control.interno.mensual`

#### Campos

| Campo | Tipo | Descripcion | Requerido |
|-------|------|-------------|-----------|
| `name` | Char | Nombre del control interno | Si |
| `mes` | Date | Mes del control (primer dia) | Si |
| `costos_gastos_ids` | One2many | Lineas de costos y gastos | No |
| `mes_fin` | Date | Ultimo dia del mes (computed) | - |
| `month_first_day` | Date | Primer dia del mes (computed) | - |

#### Metodos Publicos

```python
def cargar_datos_desde_xml(self):
    """
    Carga automaticamente facturas XML del mes en lineas de costos y gastos.

    Comportamiento:
    - Busca factura.xml entre mes y mes_fin
    - Evita duplicados por folio_fiscal
    - Determina tipo_comprobante segun pais
    - Mapea forma_pago a tipo_pago

    Returns:
        dict: Accion de recarga de vista
    """

def action_export_csv(self):
    """
    Exporta todas las lineas de costos y gastos a CSV.

    Returns:
        dict: Accion de descarga del archivo CSV
    """

def action_import_csv(self):
    """
    Abre asistente para importar datos desde CSV.

    Returns:
        dict: Accion del wizard de importacion
    """
```

#### Ejemplo de Uso

```python
# Obtener un control interno
control = self.env['control.interno.mensual'].browse(control_id)

# Acceder a las lineas de costos y gastos
for linea in control.costos_gastos_ids:
    print(f"Proveedor: {linea.proveedor_text}, Total: {linea.total}")

# Crear un nuevo control interno
nuevo_control = self.env['control.interno.mensual'].create({
    'name': 'Control Enero 2024',
    'mes': '2024-01-01',
})

# Cargar facturas XML automaticamente
nuevo_control.cargar_datos_desde_xml()
```

---

### 3.2 costos.gastos.line

**Descripcion:** Representa una linea individual de costo o gasto.

**Nombre Tecnico:** `costos.gastos.line`

#### Campos Principales

| Campo | Tipo | Descripcion | Relacion |
|-------|------|-------------|----------|
| `control_interno_id` | Many2one | Control interno padre | control.interno.mensual |
| `factura_xml_id` | Many2one | Factura XML origen | factura.xml |
| `orden_compra_id` | Many2one | Orden de compra | purchase.order |
| `proveedor_id` | Many2one | Proveedor | res.partner |
| `country_id` | Many2one | Pais | res.country |
| `moneda_id` | Many2one | Moneda | res.currency |
| `cuenta_id` | Many2one | Cuenta contable | catalogo.cuentas |

#### Campos de Datos

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `fecha_pago` | Date | Fecha de pago |
| `tipo_pago` | Selection | Tipo de pago |
| `tipo_comprobante` | Selection | Tipo de comprobante |
| `folio_fiscal` | Char | UUID de la factura |
| `no_comprobante` | Char | Numero de comprobante |
| `fecha_comprobante` | Date | Fecha del comprobante |
| `concepto` | Char | Descripcion del concepto |
| `proveedor_text` | Char | Nombre del proveedor (texto) |
| `tax_id` | Char | RFC del proveedor |
| `importe` | Float | Importe antes de descuento |
| `descuento` | Float | Descuento aplicado |
| `tipo_cambio` | Float | Tipo de cambio |
| `importe_mxn` | Float | Importe en MXN (computed) |
| `iva` | Float | IVA |
| `total` | Float | Total del comprobante |
| `retencion_iva` | Float | Retencion de IVA |
| `otras_retenciones` | Float | Otras retenciones |
| `pedimento_no` | Char | Numero de pedimento |
| `iva_pedimento` | Float | IVA en pedimento |
| `otros_impuestos_pedimento` | Float | Otros impuestos en pedimento |
| `division_subcuentas` | Char | Division en subcuentas |
| `importe_subcuenta` | Float | Importe de subcuenta |
| `descuento_subcuenta` | Float | Descuento de subcuenta |
| `total_subcuenta_sin_iva` | Float | Total subcuenta sin IVA |
| `descripcion_cuenta` | Text | Descripcion de la cuenta |
| `cuenta_num` | Text | Numero de cuenta |
| `comentarios_imago` | Text | Comentarios internos |
| `comentarios_contador` | Text | Comentarios del contador |

#### Campos Computed de Sugerencias

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `suggested_cuenta_ids` | Many2many | Cuentas sugeridas (max 3) |
| `suggested_cuenta_selection` | Many2one | Primera sugerencia |
| `suggestion_info` | Html | Info visual de sugerencias |

#### Valores Selection

**tipo_pago:**
```python
TIPO_PAGO_SELECTION = [
    ('caja_chica', 'Caja Chica'),
    ('debito', 'Debito'),
    ('credito', 'Credito'),
    ('transferencia', 'Transferencia'),
    ('otro', 'Otro'),
    ('efectivo', 'Efectivo'),
    ('cheque', 'Cheque'),
]
```

**tipo_comprobante:**
```python
TIPO_COMPROBANTE_SELECTION = [
    ('factura_nacional', 'Factura Nacional'),
    ('factura_extranjera', 'Factura Extranjera'),
    ('nota_remision', 'Nota de Remision'),
    ('pedimento', 'Pedimento'),
    ('linea_captura', 'Linea de Captura'),
    ('estado_cuenta', 'Estado de Cuenta'),
    ('recibo_caja', 'Recibo de Caja'),
    ('sin_recibo', 'Sin Recibo'),
]
```

#### Metodos Publicos

```python
def action_load_data_from_purchase_order(self):
    """
    Abre wizard para confirmar carga de datos desde OC.
    Requiere que orden_compra_id este establecido.

    Returns:
        dict: Accion del wizard

    Raises:
        ValidationError: Si no hay OC seleccionada
    """

def action_apply_suggested_account(self, cuenta_id):
    """
    Aplica una cuenta sugerida especifica.

    Args:
        cuenta_id (int): ID de catalogo.cuentas a aplicar

    Returns:
        bool: True si exitoso
    """

def action_apply_suggestion_1(self):
    """Aplica la primera sugerencia de cuenta."""

def action_apply_suggestion_2(self):
    """Aplica la segunda sugerencia de cuenta."""

def action_apply_suggestion_3(self):
    """Aplica la tercera sugerencia de cuenta."""
```

#### Metodos de Calculo de Sugerencias

```python
def _calculate_account_suggestions(self):
    """
    Calcula sugerencias de cuentas contables basadas en historial.

    Algoritmo de scoring:
    - Coincidencia proveedor_text exacta: +6 puntos
    - Coincidencia proveedor_text parcial: +4 puntos
    - Similitud de concepto: hasta +5 puntos
    - Tipo de comprobante igual: +3 puntos
    - Frecuencia de uso: hasta +3 puntos
    - Bonus gastos administracion: +2 puntos
    - Penalizacion por antiguedad: -0.3 por año

    Returns:
        list: [(cuenta_id, score_porcentaje), ...] (max 3)
    """

@staticmethod
def _normalize_text(text):
    """
    Normaliza texto para comparaciones.
    - Convierte a minusculas
    - Elimina acentos
    - Elimina espacios extra

    Args:
        text (str): Texto a normalizar

    Returns:
        str: Texto normalizado
    """
```

#### Ejemplo de Uso

```python
# Obtener una linea de costos
linea = self.env['costos.gastos.line'].browse(line_id)

# Acceder a datos relacionados
print(f"Control: {linea.control_interno_id.name}")
print(f"Factura XML: {linea.factura_xml_id.uuid}")
print(f"Orden de Compra: {linea.orden_compra_id.name}")

# Obtener sugerencias de cuentas
sugerencias = linea.suggested_cuenta_ids
for cuenta in sugerencias:
    print(f"Sugerencia: {cuenta.nombre_cuenta}")

# Crear una linea manualmente
nueva_linea = self.env['costos.gastos.line'].create({
    'control_interno_id': control_id,
    'proveedor_text': 'Mi Proveedor SA',
    'tax_id': 'MPR123456ABC',
    'concepto': 'Compra de materiales',
    'importe': 1000.00,
    'iva': 160.00,
    'total': 1160.00,
    'tipo_comprobante': 'factura_nacional',
    'tipo_pago': 'transferencia',
})
```

---

### 3.3 factura.xml

**Descripcion:** Representa una factura XML (CFDI) importada.

**Nombre Tecnico:** `factura.xml`

#### Campos

| Campo | Tipo | Descripcion | Constraint |
|-------|------|-------------|------------|
| `filename` | Char | Nombre del archivo XML | - |
| `uuid` | Char | UUID unico de la factura | UNIQUE |
| `folio` | Char | Folio de la factura | - |
| `fecha` | Date | Fecha de la factura | - |
| `proveedor_text` | Char | Nombre del proveedor | - |
| `proveedor_id` | Many2one | Proveedor (res.partner) | - |
| `rfc` | Char | RFC del proveedor | - |
| `pais_id` | Many2one | Pais (res.country) | - |
| `subtotal` | Float | Subtotal | - |
| `descuento` | Float | Descuento | - |
| `moneda_id` | Many2one | Moneda (res.currency) | - |
| `tipo_cambio` | Float | Tipo de cambio | - |
| `iva` | Float | IVA | - |
| `total` | Float | Total | - |
| `concepto` | Char | Descripcion concatenada | - |
| `forma_pago` | Char | Codigo SAT forma de pago | - |
| `ordenes_compra_ids` | Many2many | OC relacionadas | - |
| `state` | Selection | draft/validated/cancelled | - |
| `suggested_purchase_order_ids` | Many2many | OC sugeridas (computed) | - |

#### Metodos Publicos

```python
def get_tipo_pago_control_interno(self):
    """
    Convierte forma_pago SAT a tipo_pago del modulo.

    Returns:
        str or None: Codigo de tipo_pago

    Mapeo:
        '01' -> 'caja_chica' (Efectivo)
        '02' -> 'cheque'
        '03' -> 'transferencia'
        '04' -> 'credito'
        '28' -> 'debito'
    """

def action_suggest_purchase_orders(self):
    """
    Abre wizard para sugerir y vincular ordenes de compra.

    Returns:
        dict: Accion del wizard
    """
```

#### Algoritmo de Sugerencias de OC

```python
def _get_suggestions_with_scores(self):
    """
    Calcula sugerencias de OC con scores.

    Criterios de scoring:
    - RFC exacto: +3 puntos
    - Nombre proveedor >60% similar: +2 puntos
    - Diferencia monto <10%: +2 puntos
    - Fecha dentro de 7 dias: +1 punto
    - Mismo mes y año: +2 puntos

    Umbral minimo: 4 puntos

    Returns:
        list: [(purchase_order, score), ...]
    """
```

#### Ejemplo de Uso

```python
# Buscar facturas XML de un proveedor
facturas = self.env['factura.xml'].search([
    ('rfc', '=', 'ABC123456XYZ'),
    ('fecha', '>=', '2024-01-01'),
    ('fecha', '<=', '2024-01-31'),
])

# Obtener tipo de pago para control interno
for factura in facturas:
    tipo_pago = factura.get_tipo_pago_control_interno()
    print(f"UUID: {factura.uuid}, Tipo Pago: {tipo_pago}")

# Acceder a sugerencias de OC
factura = self.env['factura.xml'].browse(factura_id)
for oc in factura.suggested_purchase_order_ids:
    print(f"OC Sugerida: {oc.name}")
```

---

### 3.4 catalogo.cuentas

**Descripcion:** Catalogo de cuentas contables para clasificacion.

**Nombre Tecnico:** `catalogo.cuentas`

#### Campos

| Campo | Tipo | Descripcion | Requerido |
|-------|------|-------------|-----------|
| `nombre_cuenta` | Char | Nombre de la cuenta | Si |
| `numero_cuenta` | Char | Numero de la cuenta | Si |
| `descripcion` | Text | Descripcion detallada | No |

#### Metodos Publicos

```python
def name_get(self):
    """
    Retorna nombre en formato "[numero] nombre".

    Returns:
        list: [(id, display_name), ...]
    """

def name_search(self, name='', args=None, operator='ilike', limit=100):
    """
    Busca por numero o nombre de cuenta.

    Args:
        name: Termino de busqueda
        args: Dominio adicional
        operator: Operador de busqueda
        limit: Limite de resultados

    Returns:
        list: Resultados de busqueda
    """
```

#### Ejemplo de Uso

```python
# Buscar cuenta por numero
cuenta = self.env['catalogo.cuentas'].search([
    ('numero_cuenta', '=', '601-001')
], limit=1)

# Crear nueva cuenta
nueva_cuenta = self.env['catalogo.cuentas'].create({
    'nombre_cuenta': 'Gastos de Oficina',
    'numero_cuenta': '602-001',
    'descripcion': 'Gastos relacionados con suministros de oficina',
})

# Buscar cuentas por nombre
cuentas = self.env['catalogo.cuentas'].name_search('gasto', limit=10)
```

---

### 3.5 purchase.order (Extension)

**Descripcion:** Extension del modelo purchase.order con campo de control interno.

**Nombre Tecnico:** `purchase.order` (heredado)

#### Campos Añadidos

| Campo | Tipo | Descripcion | Default |
|-------|------|-------------|---------|
| `control_interno` | Boolean | Indica si la OC esta en control interno | False |

#### Comportamiento Automatico

El campo `control_interno` se actualiza automaticamente:

- **Al crear `costos.gastos.line` con OC:** Se marca `control_interno = True`
- **Al eliminar `costos.gastos.line`:** Si no quedan otras lineas, se marca `control_interno = False`
- **Al cambiar OC en linea:** Se actualiza en ambas OC (anterior y nueva)

#### Ejemplo de Uso

```python
# Buscar OC que no estan en control interno
oc_disponibles = self.env['purchase.order'].search([
    ('control_interno', '=', False),
    ('state', 'in', ['purchase', 'done']),
])

# Verificar si una OC esta en control
oc = self.env['purchase.order'].browse(oc_id)
if oc.control_interno:
    print("Esta OC ya esta incluida en un control interno")
```

---

## 4. API Publica y Metodos de Integracion

### 4.1 Crear Lineas de Control Interno Programaticamente

```python
def crear_linea_control_interno(self, control_id, datos):
    """
    Ejemplo de como crear una linea de control interno.
    """
    control = self.env['control.interno.mensual'].browse(control_id)

    linea = self.env['costos.gastos.line'].create({
        'control_interno_id': control.id,
        'proveedor_text': datos.get('proveedor'),
        'tax_id': datos.get('rfc'),
        'concepto': datos.get('concepto'),
        'importe': datos.get('importe', 0.0),
        'descuento': datos.get('descuento', 0.0),
        'iva': datos.get('iva', 0.0),
        'total': datos.get('total', 0.0),
        'tipo_comprobante': datos.get('tipo_comprobante', 'factura_nacional'),
        'tipo_pago': datos.get('tipo_pago', 'transferencia'),
        'fecha_comprobante': datos.get('fecha'),
        'folio_fiscal': datos.get('uuid'),
        # Relacionar con OC si existe
        'orden_compra_id': datos.get('orden_compra_id'),
        # Relacionar con factura XML si existe
        'factura_xml_id': datos.get('factura_xml_id'),
    })

    return linea
```

### 4.2 Buscar Facturas XML por Criterios

```python
def buscar_facturas_xml(self, rfc=None, fecha_desde=None, fecha_hasta=None, monto_min=None):
    """
    Ejemplo de busqueda de facturas XML.
    """
    domain = []

    if rfc:
        domain.append(('rfc', '=', rfc))
    if fecha_desde:
        domain.append(('fecha', '>=', fecha_desde))
    if fecha_hasta:
        domain.append(('fecha', '<=', fecha_hasta))
    if monto_min:
        domain.append(('total', '>=', monto_min))

    return self.env['factura.xml'].search(domain)
```

### 4.3 Vincular Factura XML con Orden de Compra

```python
def vincular_factura_oc(self, factura_xml_id, purchase_order_id):
    """
    Vincula una factura XML con una orden de compra.
    """
    factura = self.env['factura.xml'].browse(factura_xml_id)
    oc = self.env['purchase.order'].browse(purchase_order_id)

    # Añadir OC a la factura
    factura.write({
        'ordenes_compra_ids': [(4, oc.id)]
    })

    # Actualizar lineas de control interno relacionadas
    lineas = self.env['costos.gastos.line'].search([
        ('factura_xml_id', '=', factura.id)
    ])

    for linea in lineas:
        linea.write({'orden_compra_id': oc.id})

    return True
```

### 4.4 Obtener Sugerencias de Cuentas

```python
def obtener_sugerencias_cuenta(self, proveedor_text, concepto, tipo_comprobante):
    """
    Obtiene sugerencias de cuentas basadas en criterios.
    """
    # Crear linea temporal para calcular sugerencias
    linea_temp = self.env['costos.gastos.line'].new({
        'proveedor_text': proveedor_text,
        'concepto': concepto,
        'tipo_comprobante': tipo_comprobante,
    })

    # Calcular sugerencias
    linea_temp._compute_suggested_cuentas()

    return linea_temp.suggested_cuenta_ids
```

---

## 5. Puntos de Extension

### 5.1 Heredar Modelos

#### Extender costos.gastos.line

```python
# mi_modulo/models/costos_gastos_line_extension.py

from odoo import models, fields, api

class CostosGastosLineExtension(models.Model):
    _inherit = 'costos.gastos.line'

    # Añadir nuevos campos
    mi_campo_custom = fields.Char(string='Mi Campo')
    proyecto_id = fields.Many2one('project.project', string='Proyecto')

    # Sobrescribir metodos
    @api.model
    def create(self, vals):
        # Logica personalizada antes de crear
        result = super().create(vals)
        # Logica personalizada despues de crear
        return result

    # Añadir nuevos metodos
    def mi_metodo_custom(self):
        for record in self:
            # Logica personalizada
            pass
```

#### Extender control.interno.mensual

```python
class ControlInternoMensualExtension(models.Model):
    _inherit = 'control.interno.mensual'

    # Añadir campos computed
    total_gastos = fields.Float(
        string='Total Gastos',
        compute='_compute_total_gastos',
        store=True
    )

    @api.depends('costos_gastos_ids', 'costos_gastos_ids.total')
    def _compute_total_gastos(self):
        for record in self:
            record.total_gastos = sum(record.costos_gastos_ids.mapped('total'))
```

### 5.2 Heredar Vistas

#### Añadir Campos a la Vista Form

```xml
<!-- mi_modulo/views/costos_gastos_line_views.xml -->

<odoo>
    <record id="view_costos_gastos_line_form_inherit" model="ir.ui.view">
        <field name="name">costos.gastos.line.form.inherit</field>
        <field name="model">costos.gastos.line</field>
        <field name="inherit_id" ref="om_control_interno.view_costos_gastos_line_form"/>
        <field name="arch" type="xml">
            <!-- Añadir campo despues de concepto -->
            <xpath expr="//field[@name='concepto']" position="after">
                <field name="mi_campo_custom"/>
                <field name="proyecto_id"/>
            </xpath>
        </field>
    </record>
</odoo>
```

#### Añadir Columnas al Tree

```xml
<record id="view_costos_gastos_line_tree_inherit" model="ir.ui.view">
    <field name="name">costos.gastos.line.tree.inherit</field>
    <field name="model">costos.gastos.line</field>
    <field name="inherit_id" ref="om_control_interno.view_costos_gastos_line_tree"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='total']" position="after">
            <field name="proyecto_id"/>
        </xpath>
    </field>
</record>
```

### 5.3 Añadir Menus

```xml
<!-- Añadir submenu bajo Control Interno -->
<menuitem id="menu_mi_funcionalidad"
    name="Mi Funcionalidad"
    parent="om_control_interno.menu_control_interno_sub"
    action="mi_action"
    sequence="30"/>
```

### 5.4 Eventos y Triggers

#### Usar Onchange

```python
@api.onchange('factura_xml_id')
def _onchange_factura_xml_custom(self):
    """Se ejecuta cuando cambia la factura XML."""
    if self.factura_xml_id:
        # Tu logica personalizada
        self.mi_campo_custom = self.factura_xml_id.concepto[:50]
```

#### Sobrescribir Write

```python
def write(self, vals):
    result = super().write(vals)

    if 'cuenta_id' in vals:
        # Logica cuando se asigna una cuenta
        for record in self:
            self._notificar_asignacion_cuenta(record)

    return result
```

---

## 6. Ejemplos de Integracion

### 6.1 Modulo de Proyectos con Control Interno

```python
# mi_modulo_proyecto/__manifest__.py
{
    'name': 'Proyecto - Control Interno',
    'depends': ['om_control_interno', 'project'],
    'data': [
        'views/costos_gastos_line_views.xml',
    ],
}

# mi_modulo_proyecto/models/costos_gastos_line.py
from odoo import models, fields, api

class CostosGastosLineProyecto(models.Model):
    _inherit = 'costos.gastos.line'

    proyecto_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        help='Proyecto al que se asigna este gasto'
    )

    @api.onchange('orden_compra_id')
    def _onchange_orden_compra_proyecto(self):
        """Hereda el proyecto de la OC si existe."""
        if self.orden_compra_id and hasattr(self.orden_compra_id, 'proyecto_id'):
            self.proyecto_id = self.orden_compra_id.proyecto_id
```

### 6.2 Modulo de Reportes

```python
# mi_modulo_reportes/models/reporte_control_interno.py
from odoo import models, fields, api

class ReporteControlInterno(models.TransientModel):
    _name = 'reporte.control.interno'
    _description = 'Reporte de Control Interno'

    control_interno_id = fields.Many2one(
        'control.interno.mensual',
        string='Control Interno',
        required=True
    )
    tipo_reporte = fields.Selection([
        ('resumen', 'Resumen'),
        ('detallado', 'Detallado'),
        ('por_proveedor', 'Por Proveedor'),
    ], string='Tipo de Reporte', default='resumen')

    def generar_reporte(self):
        self.ensure_one()
        control = self.control_interno_id
        lineas = control.costos_gastos_ids

        if self.tipo_reporte == 'resumen':
            data = {
                'total_lineas': len(lineas),
                'total_importe': sum(lineas.mapped('total')),
                'total_iva': sum(lineas.mapped('iva')),
                'por_tipo_pago': {},
            }

            for tipo in ['caja_chica', 'debito', 'credito', 'transferencia']:
                lineas_tipo = lineas.filtered(lambda l: l.tipo_pago == tipo)
                data['por_tipo_pago'][tipo] = {
                    'cantidad': len(lineas_tipo),
                    'total': sum(lineas_tipo.mapped('total')),
                }

            return data

        # ... otros tipos de reporte
```

### 6.3 Integracion con Contabilidad

```python
# mi_modulo_contabilidad/models/asiento_contable.py
from odoo import models, fields, api

class AsientoControlInterno(models.Model):
    _inherit = 'account.move'

    control_interno_line_id = fields.Many2one(
        'costos.gastos.line',
        string='Linea de Control Interno',
        help='Linea de control interno que origino este asiento'
    )

class CostosGastosLineContabilidad(models.Model):
    _inherit = 'costos.gastos.line'

    asiento_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        readonly=True
    )

    def action_crear_asiento(self):
        """Crea un asiento contable basado en la linea."""
        self.ensure_one()

        if not self.cuenta_id:
            raise ValidationError("Debe asignar una cuenta contable primero.")

        # Buscar cuenta contable de Odoo
        account = self.env['account.account'].search([
            ('code', '=', self.cuenta_num)
        ], limit=1)

        if not account:
            raise ValidationError(f"No existe cuenta contable con codigo {self.cuenta_num}")

        move_vals = {
            'journal_id': self._get_journal_id(),
            'date': self.fecha_comprobante,
            'ref': self.folio_fiscal or self.no_comprobante,
            'control_interno_line_id': self.id,
            'line_ids': [
                (0, 0, {
                    'name': self.concepto,
                    'account_id': account.id,
                    'debit': self.total,
                    'credit': 0.0,
                    'partner_id': self.proveedor_id.id,
                }),
                # ... contrapartida
            ],
        }

        move = self.env['account.move'].create(move_vals)
        self.asiento_id = move.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }
```

---

## 7. Widgets JavaScript Personalizados

### 7.1 date_anchor_control_month

Widget de fecha que abre el selector en el mes del control interno.

**Uso en XML:**
```xml
<field name="fecha_pago" widget="date_anchor_control_month"/>
```

**Comportamiento:**
- Lee el campo `mes` relacionado
- Abre el date picker en ese mes
- Opcion `prefill_on_edit` para pre-llenar en edicion

### 7.2 date_control_month

Widget de fecha controlado por contexto.

**Uso en XML:**
```xml
<field name="fecha_comprobante"
       widget="date_control_month"
       context="{'control_month_first_day': mes, 'prefill_on_edit': True}"/>
```

**Opciones de contexto:**
- `control_month_first_day`: Fecha del primer dia del mes
- `only_on_edit`: Solo aplicar en modo edicion
- `prefill_on_edit`: Pre-llenar fecha al editar

---

## 8. Constantes y Mapeos

### 8.1 Mapeo Forma de Pago SAT a Tipo de Pago

```python
FORMA_PAGO_TO_TIPO_PAGO = {
    '1': 'caja_chica',    # Efectivo
    '01': 'caja_chica',   # Efectivo (con cero)
    '2': 'cheque',        # Cheque nominativo
    '02': 'cheque',
    '3': 'transferencia', # Transferencia electronica
    '03': 'transferencia',
    '4': 'credito',       # Tarjeta de credito
    '04': 'credito',
    '28': 'debito',       # Tarjeta de debito
    '028': 'debito',
}
```

### 8.2 Mapeo de Tipos de Comprobante (Importacion CSV)

```python
TIPO_COMPROBANTE_MAP = {
    'factura nacional': 'factura_nacional',
    'factura extranjera': 'factura_extranjera',
    'nota de remision': 'nota_remision',
    'nota remision': 'nota_remision',
    'pedimento': 'pedimento',
    'linea de captura': 'linea_captura',
    'linea captura': 'linea_captura',
    'estado de cuenta': 'estado_cuenta',
    'estado cuenta': 'estado_cuenta',
    'recibo de caja': 'recibo_caja',
    'recibo caja': 'recibo_caja',
    'sin recibo': 'sin_recibo',
}
```

### 8.3 Mapeo de Tipos de Pago (Importacion CSV)

```python
TIPO_PAGO_MAP = {
    'caja chica': 'caja_chica',
    'debito': 'debito',
    'credito': 'credito',
    'transferencia': 'transferencia',
    'otro': 'otro',
    'efectivo': 'efectivo',
    'cheque': 'cheque',
}
```

---

## 9. Consideraciones de Rendimiento

### 9.1 Limites de Busqueda

- **Sugerencias de cuentas:** Busca maximo 500 registros historicos
- **Sugerencias de OC:** Rango de fechas: mes anterior a mes posterior

### 9.2 Campos Computed

Los siguientes campos son computed y pueden impactar rendimiento:

| Campo | Modelo | Store |
|-------|--------|-------|
| `mes_fin` | control.interno.mensual | No |
| `month_first_day` | control.interno.mensual | No |
| `importe_mxn` | costos.gastos.line | No |
| `suggested_cuenta_ids` | costos.gastos.line | No |
| `suggestion_info` | costos.gastos.line | No |
| `suggested_purchase_order_ids` | factura.xml | No |

### 9.3 Indices SQL

- `factura.xml.uuid`: UNIQUE constraint (indice automatico)

### 9.4 Recomendaciones

1. **Evitar N+1 queries:** Usar `mapped()` y `filtered()` en lugar de iteraciones
2. **Prefetch:** Usar `sudo()` con cuidado, preferir context con `prefetch_fields`
3. **Batch processing:** Para importaciones masivas, usar `create()` con lista de valores

```python
# Malo (N+1)
for record in records:
    print(record.proveedor_id.name)

# Bueno (prefetch automatico)
for record in records.with_context(prefetch_fields=['proveedor_id']):
    print(record.proveedor_id.name)

# O mejor aun
proveedores = records.mapped('proveedor_id.name')
```

---

## 10. Preguntas Frecuentes

### ¿Como añadir un nuevo tipo de pago?

Debes heredar el modelo y extender el campo Selection:

```python
class CostosGastosLineExtension(models.Model):
    _inherit = 'costos.gastos.line'

    tipo_pago = fields.Selection(
        selection_add=[
            ('criptomoneda', 'Criptomoneda'),
            ('paypal', 'PayPal'),
        ]
    )
```

### ¿Como integrar con el proceso de aprobacion?

Puedes añadir un campo de estado y flujo de trabajo:

```python
class CostosGastosLineAprobacion(models.Model):
    _inherit = 'costos.gastos.line'

    estado_aprobacion = fields.Selection([
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente Aprobacion'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ], default='borrador')

    def action_solicitar_aprobacion(self):
        self.write({'estado_aprobacion': 'pendiente'})

    def action_aprobar(self):
        self.write({'estado_aprobacion': 'aprobado'})
```

### ¿Como personalizar el algoritmo de sugerencias de cuentas?

Sobrescribe el metodo `_calculate_account_suggestions`:

```python
class CostosGastosLineCustomSuggestions(models.Model):
    _inherit = 'costos.gastos.line'

    def _calculate_account_suggestions(self):
        # Tu algoritmo personalizado
        # O llamar al original y modificar resultados
        suggestions = super()._calculate_account_suggestions()

        # Añadir tu logica
        return suggestions
```

---

## 11. Soporte y Recursos

### Estructura de Archivos para Nuevo Modulo

```
mi_modulo_integracion/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   └── mi_extension.py
├── views/
│   └── mi_extension_views.xml
├── security/
│   └── ir.model.access.csv
└── data/
    └── mi_data.xml
```

### Manifest Ejemplo

```python
# __manifest__.py
{
    'name': 'Mi Modulo - Control Interno',
    'version': '14.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Integracion con Control Interno',
    'depends': ['om_control_interno'],
    'data': [
        'security/ir.model.access.csv',
        'views/mi_extension_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
```

---

## Changelog

| Version | Fecha | Descripcion |
|---------|-------|-------------|
| 1.0 | 2024-01 | Version inicial del manual |

---

*Documento generado para om_control_interno v1.0 - Odoo 14 CE*
