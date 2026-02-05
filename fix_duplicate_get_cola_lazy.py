#!/usr/bin/env python3
"""
Script para eliminar la función duplicada get_cola_lazy (línea 2096)
"""
import re

# Leer el archivo
with open('crud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar las líneas donde comienzan las definiciones de get_cola_lazy
definition_lines = []
for i, line in enumerate(lines):
    if re.match(r'^def get_cola_lazy\(db: Session\):', line):
        definition_lines.append(i)

print(f"Encontradas {len(definition_lines)} definiciones de get_cola_lazy en líneas: {[i+1 for i in definition_lines]}")

if len(definition_lines) >= 2:
    # Encontrar dónde termina la primera función (siguiente función def)
    first_def_line = definition_lines[0]
    second_def_line = definition_lines[1]
    
    # La primera función termina justo antes de la segunda
    end_of_first = second_def_line
    
    print(f"\nEliminando función duplicada de línea {first_def_line + 1} a línea {end_of_first}")
    print(f"Línea {first_def_line + 1}: {lines[first_def_line].strip()}")
    print(f"Línea {end_of_first}: {lines[end_of_first].strip()}")
    
    # Eliminar las líneas duplicadas
    new_lines = lines[:first_def_line] + lines[second_def_line:]
    
    # Escribir el archivo de vuelta
    with open('crud.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"\n✅ Archivo actualizado. Eliminadas {end_of_first - first_def_line} líneas.")
else:
    print("⚠️  No se encontraron suficientes definiciones para eliminar duplicadas")
