#__manifest__.py

{
    'name': 'Control Interno',
    'version': '1.0',
    'summary': 'Módulo para llevar un control interno de facturas',
    'author': 'Tu Nombre',
    'depends': ['account', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/control_interno_views.xml',
        'views/factura_xml_views.xml',
        'views/catalogo_cuentas_views.xml',
        'views/factura_xml_purchase_order_wizard_views.xml',
        'views/control_interno_menus.xml',
    ],
    'installable': True,
    'application': True,
}
