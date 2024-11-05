#!/bin/zsh

# Script para unir archivos de texto (.txt, .py, .xml, .csv) en un solo archivo,
# indicando el nombre y la ruta relativa de cada archivo al inicio de su contenido.

# Uso: ./merge_texts.zsh [directorio] [archivo_salida]

# Definir el directorio a procesar (por defecto, el directorio actual)
DIRECTORY=${1:-.}

# Definir el archivo de salida (por defecto, merged_output.txt)
OUTPUT_FILE=${2:-merged_output.txt}

# Verificar si el directorio existe
if [[ ! -d "$DIRECTORY" ]]; then
    echo "Error: El directorio '$DIRECTORY' no existe."
    exit 1
fi

# Eliminar el archivo de salida si ya existe para evitar duplicados
if [[ -f "$OUTPUT_FILE" ]]; then
    rm "$OUTPUT_FILE"
fi

# Buscar y procesar los archivos
find "$DIRECTORY" -type f \( -iname "*.txt" -o -iname "*.py" -o -iname "*.xml" -o -iname "*.csv" \) | while IFS= read -r FILE
do
    # Obtener la ruta relativa respecto al directorio base
    REL_PATH=${FILE#"$DIRECTORY"/}

    # Escribir el encabezado en el archivo de salida
    echo "===== Archivo: $REL_PATH =====" >> "$OUTPUT_FILE"

    # Insertar el contenido del archivo
    cat "$FILE" >> "$OUTPUT_FILE"

    # Agregar una línea en blanco para separar los contenidos
    echo -e "\n" >> "$OUTPUT_FILE"
done

echo "Todos los archivos han sido unidos en '$OUTPUT_FILE'."
