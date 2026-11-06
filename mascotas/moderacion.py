"""
moderacion.py — Detección y censura de palabras ofensivas  (casos 1.1 y 2.2)
-----------------------------------------------------------------------------
Cómo funciona:
  1. Separa el texto en palabras.
  2. "Normaliza" cada palabra para que no se pueda esquivar el filtro:
       - minúsculas y sin tildes            (HUEÓN   → hueon)
       - números/símbolos que imitan letras (w3on    → weon, put@ → puta)
       - letras repetidas                   (weoooon → weon)
       - puntos o guiones entre letras      (p.u.t.a → puta)
  3. Compara contra la lista de palabras prohibidas (y sus variantes).

Para agregar palabras, edita PALABRAS o PATRONES (en minúsculas, sin tildes).
Ojo: "perra", "perro", "zorra" NO están porque son nombres de animales.
"""
import re
import unicodedata

# Palabras exactas (ya normalizadas)
PALABRAS = {
    'puta', 'putas', 'puto', 'putos', 'hdp', 'ctm', 'csm', 'ptm', 'qlo', 'ql', 'qliao',
    'mierda', 'mierdas', 'chucha', 'conchetumare', 'conchetumadre', 'conchesumadre',
    'conchasumadre', 'conchatumadre', 'conchesumare', 'culiao', 'culiaos', 'culiado',
    'culiados', 'culia', 'culiada', 'culiadas', 'pichula', 'pichulas', 'verga', 'vergas',
    'imbecil', 'imbeciles', 'idiota', 'idiotas', 'estupido', 'estupida', 'estupidos',
    'estupidas', 'pendejo', 'pendeja', 'pendejos', 'cabron', 'cabrona', 'cabrones',
    'malparido', 'malparida', 'maraca', 'maracas', 'maricon', 'maricones', 'marica',
    'mariconazo', 'hijueputa', 'hijoeputa', 'sacowea', 'retrasado', 'retrasada', 'mongolico',
    'mongolica', 'tarado', 'tarada', 'pelotudo', 'pelotuda', 'forro', 'boludo', 'boluda',
    'fuck', 'fucking', 'shit', 'bitch', 'asshole', 'motherfucker', 'nigger', 'nigga',
}

# Variantes con terminaciones (weon, weona, aweonao, huevon, gueones…)
PATRONES = [
    re.compile(r'^a?(we|hue|gue|wue)on(a|as|es|ao|aos|ada|adas|cito|cita|azo)?$'),
    re.compile(r'^a?weonao?s?$'),
    re.compile(r'^(conch|conx)[ae]?(tu|su|e)?ma(dre|re)s?$'),
    re.compile(r'^put(it)?[ao]s?$'),
    re.compile(r'^mierd(a|as|ita|itas|oso|osa)$'),
    re.compile(r'^culi(ao|ado|ada|aos|ados|adas|a)$'),
]

# Números y símbolos que la gente usa para reemplazar letras
SUSTITUCIONES = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b',
    '@': 'a', '$': 's', '!': 'i', '|': 'l', '€': 'e',
})

# Una "palabra" = letras, números o símbolos de reemplazo, permitiendo . - _ * entre letras
REGEX_PALABRA = re.compile(r"[\w@$€]+(?:[.\-_*!|]*[\w@$€]+)*", re.UNICODE)


def _sin_tildes(texto):
    descompuesto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in descompuesto if unicodedata.category(c) != 'Mn')


def normalizar(palabra):
    p = _sin_tildes(palabra.lower()).translate(SUSTITUCIONES)
    p = re.sub(r'[.\-_*|]', '', p)       # p.u.t.a → puta
    p = re.sub(r'(.)\1+', r'\1', p)       # weoooon → weon
    return p


def es_ofensiva(palabra):
    p = normalizar(palabra)
    if len(p) < 2:
        return False
    # También probamos sin colapsar dobles letras legítimas ("conchetumarre")
    candidatos = {p, re.sub(r'(.)\1+', r'\1', _sin_tildes(palabra.lower()).translate(SUSTITUCIONES))}
    for c in candidatos:
        if c in PALABRAS or any(patron.match(c) for patron in PATRONES):
            return True
    return False


def contiene_ofensivas(texto):
    return any(es_ofensiva(m.group()) for m in REGEX_PALABRA.finditer(texto or ''))


def censurar(texto):
    """Reemplaza cada palabra ofensiva por su primera letra + asteriscos:  'weon' → 'w***'."""
    if not texto:
        return texto
    return REGEX_PALABRA.sub(
        lambda m: m.group()[0] + '*' * (len(m.group()) - 1) if es_ofensiva(m.group()) else m.group(),
        texto,
    )
