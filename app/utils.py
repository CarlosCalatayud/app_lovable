# Mapeo de provincia a 'slug' de comunidad autónoma.
# El slug se usará para encontrar la carpeta de plantillas correcta.
PROVINCE_TO_COMMUNITY_MAP = {
    # Andalucía
    "Almería": "andalucia", "Cádiz": "andalucia", "Córdoba": "andalucia", "Granada": "andalucia",
    "Huelva": "andalucia", "Jaén": "andalucia", "Málaga": "andalucia", "Sevilla": "andalucia",
    # Aragón
    "Huesca": "aragon", "Teruel": "aragon", "Zaragoza": "aragon",
    # Asturias
    "Asturias": "asturias",
    # Baleares
    "Baleares": "baleares", "Illes Balears": "baleares",
    # Canarias
    "Las Palmas": "canarias", "Santa Cruz de Tenerife": "canarias",
    # Cantabria
    "Cantabria": "cantabria",
    # Castilla y León
    "Ávila": "castilla_y_leon", "Burgos": "castilla_y_leon", "León": "castilla_y_leon",
    "Palencia": "castilla_y_leon", "Salamanca": "castilla_y_leon", "Segovia": "castilla_y_leon",
    "Soria": "castilla_y_leon", "Valladolid": "castilla_y_leon", "Zamora": "castilla_y_leon",
    # Castilla-La Mancha
    "Albacete": "castilla_la_mancha", "Ciudad Real": "castilla_la_mancha", "Cuenca": "castilla_la_mancha",
    "Guadalajara": "castilla_la_mancha", "Toledo": "castilla_la_mancha",
    # Cataluña
    "Barcelona": "catalunya", "Girona": "catalunya", "Lleida": "catalunya", "Tarragona": "catalunya",
    # Comunidad Valenciana
    "Alicante": "comunitat_valenciana", "Castellón": "comunitat_valenciana", "Valencia": "comunitat_valenciana",
    # Extremadura
    "Badajoz": "extremadura", "Cáceres": "extremadura",
    # Galicia
    "A Coruña": "galicia", "Lugo": "galicia", "Ourense": "galicia", "Pontevedra": "galicia",
    # Madrid
    "Madrid": "madrid",
    # Murcia
    "Murcia": "murcia",
    # Navarra
    "Navarra": "navarra",
    # País Vasco
    "Álava": "pais_vasco", "Gipuzkoa": "pais_vasco", "Bizkaia": "pais_vasco",
    # La Rioja
    "La Rioja": "rioja",
    # Ciudades Autónomas
    "Ceuta": "ceuta",
    "Melilla": "melilla",
}

# Diccionario de 'slug' a nombre legible para mostrar en el frontend.
COMMUNITIES = {
    "andalucia": "Andalucía", "aragon": "Aragón", "asturias": "Asturias, Principado de",
    "baleares": "Balears, Illes", "canarias": "Canarias", "cantabria": "Cantabria",
    "castilla_y_leon": "Castilla y León", "castilla_la_mancha": "Castilla-La Mancha",
    "catalunya": "Cataluña", "comunitat_valenciana": "Comunitat Valenciana",
    "extremadura": "Extremadura", "galicia": "Galicia", "madrid": "Madrid, Comunidad de",
    "murcia": "Murcia, Región de", "navarra": "Navarra, Comunidad Foral de",
    "pais_vasco": "País Vasco", "rioja": "Rioja, La", "ceuta": "Ceuta", "melilla": "Melilla"
}