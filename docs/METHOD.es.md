# Para especialistas

_Generado desde `web/strings.json` con `python -m web.method_doc`; el mismo texto está en https://zohar.digital/es/scholars. No editar a mano._ · [English](METHOD.md)

Método, procedencia, datos y cita. Ningún número de este sitio lo produce un modelo: cuenta un código determinista, el modelo solo traduce e interpreta, y cada paso se detalla aquí.

Código y datos: https://github.com/Jossifresben/zohar-symbols · DOI [10.5281/zenodo.23305097](https://doi.org/10.5281/zenodo.23305097)

## Método

**Corpus y estratos.** El texto es el Zohar de Wikisource hebreo, con la paginación de Mantua, tomado de sus 29 páginas de parashá. Los pasajes son los párrafos de cada folio. Las etiquetas de sección y los títulos de los editores distinguen nueve corrientes de texto (principal, Ra'aya Meheimna, Midrash ha-Ne'lam, Sitrei Torá, Raza de-Razín, Tosefta, Matnitín, otros, apéndice). Cada corriente distinta de la principal es un estrato propio. Los pasajes de la corriente principal que caen dentro de los rangos convencionales de Idra Rabá e Idra Zutá de seeds/strata.tsv pasan a esos estratos, y los que caen dentro de los rangos del Midrash ha-Ne'lam de Shemot (II 4a–5b, 14a–21b; texto que Wikisource deja sin etiqueta) se suman al estrato Midrash ha-Ne'lam; el resto de la corriente principal sigue siendo «principal». En total hay once estratos: principal, Idra Rabá, Idra Zutá y las ocho corrientes etiquetadas.

**Lematización.** Cada palabra se reduce a una raíz cuando es posible, con el Atlas de Raíces Arameas (aramaic_core) y una tabla de excepciones propia del Zohar, que prevalece sobre aramaic_core. Las excepciones se buscan también tras los proclíticos ו ד ב ל כ מ ש. Una excepción con la raíz vacía marca un token no léxico conocido, como la abreviatura הקב״ה. Las palabras que el extractor no logra ubicar se conservan y se cuentan como desconocidas.

**Etiquetado de menciones.** Un símbolo se etiqueta por sus alias de superficie (admitiendo pares seguros de proclíticos) y por sus raíces distintivas; en un mismo token, un alias de superficie prevalece sobre una coincidencia por raíz. En los alias de varias palabras gana la coincidencia más larga. La palabra que sigue inmediatamente a רבי, ר׳, א״ר o רב no se etiqueta en absoluto, ni por alias de una sola palabra ni por raíz, porque es el nombre de un sabio; los alias de varias palabras quedan exentos de esta regla.

**Coocurrencia y PMI.** Dos símbolos coocurren en un pasaje (un párrafo de folio) solo cuando cada uno tiene al menos una mención en un token que el otro no etiqueta; un símbolo cuyos tokens son un subconjunto de los del otro es un rival, no un acompañante. PMI = log2(c·N / (fa·fb)), donde c es el número de pasajes en que coocurre el par, fa y fb son los pasajes que mencionan cada símbolo y N es el total de pasajes. Solo se muestra para los pares con al menos 5 pasajes en común.

**Estados.** El estado de un símbolo (por ejemplo, en plenitud o en mengua) se detecta en un pasaje que menciona el símbolo cuando en él aparece cualquiera de las raíces marcadoras declaradas para ese estado. Los marcadores se declaran en la semilla; no se infieren.

**Pasajes destacados.** Los candidatos son los pasajes que mencionan el símbolo. Cada uno recibe la puntuación (2·menciones propias + menciones de los tres acompañantes principales del símbolo) / (tokens + 20). Tienen prioridad los pasajes de al menos 12 tokens y, entre ellos, va primero uno por estrato y después el resto por puntuación; los más cortos solo se usan para completar seis. Los empates se resuelven por el id del pasaje (orden de folio).

**Recuento bruto y recuento resuelto.** El recuento bruto incluye todas las menciones etiquetadas. Cuando dos o más símbolos se etiquetan en el mismo token, la mención se descarta del recuento resuelto de un símbolo solo si un rival en ese token tiene estrictamente más apoyo que el propio símbolo; en caso de empate se conservan ambos. El apoyo de un símbolo es el número de símbolos de su nodo presentes en el pasaje, sin contar ninguno de los símbolos etiquetados en el token compartido. El apoyo no se normaliza por el tamaño del nodo, de modo que los nodos con muchos símbolos en la semilla (Maljut) ganan más a menudo. El recuento bruto se muestra siempre junto al resuelto.

## Procedencia

Fuentes de la semilla. Los símbolos y sus alias provienen del Pardes Rimonim de Cordovero (puerta 23), del Sha'arei Orah de Gikatilla, del uso del propio Zohar y de añadidos. Cada símbolo registra su fuente.

Cifras de esta construcción (pasajes, tokens, raíces, menciones, pares, traducciones, interpretaciones): [data/report.md](../data/report.md).

Salvedades. Los rangos de los estratos son convencionales. La parashá es una etiqueta de página, no una propiedad de cada pasaje. Falta una verificación académica de los límites del Midrash ha-Ne'lam y de los apéndices. Ningún pasaje lleva el número Zohar III 116a–b. Wikisource no marca ningún folio 116, y los tres comentarios clásicos de Sefaria (Or HaJamá, Mikdash Mélej, Yahel Or) tampoco comentan nada allí; el 115b tiene una extensión normal y Bamidbar empieza en el 117a. Parece un salto en la numeración impresa, no un texto perdido, aunque no se ha cotejado con un facsímil del impreso.

## Traducciones e interpretaciones

**Traducciones.** 678 pasajes destacados (los pasajes más fuertes de cada símbolo, sin duplicados) se traducen del arameo al inglés y al español, cada lengua directamente desde el arameo, con Claude Fable 5.1 (claude-fable-5-1) mediante la Batch API de Anthropic. El modelo recibe el pasaje, dos párrafos a cada lado como contexto, el versículo comentado y un glosario con la etiqueta de cada símbolo, para que las imágenes conserven los nombres del diccionario. Se le pide que mantenga las imágenes como imágenes («la luna» sigue siendo «la luna») y que no las descifre; Teshuvá conserva su nombre, glosado como «el retorno de la he».

**Interpretaciones.** Bajo 677 de esas traducciones, «Qué significa este pasaje» es una lectura en lenguaje llano de unas 120–200 palabras en cada lengua (algunas son más largas), del mismo modelo. Recibe el pasaje, sus vecinos, nuestra traducción inglesa y las claves del pasaje (cada imagen y la sefirá que suele representar), y se le pide que diga qué ocurre, qué representan las imágenes y por qué importa; que explique cada término técnico; que lo diga cuando un pasaje queda abierto; y que no use términos cabalísticos posteriores (partzufim, tzimtzum) salvo que el pasaje los use. No recibe ningún comentario ni cita ninguno: en una prueba a ciegas, las lecturas escritas con los comentarios clásicos Or HaJamá y Mikdash Mélej como trasfondo no fueron preferidas a las simples. El modelo declinó un pasaje (III 128a, Idra Rabá), que no tiene interpretación.

**Controles y procedencia.** Es el código, no el modelo, el que revisa cada resultado: su forma, su extensión, y que no use términos posteriores ni nombre a ningún comentarista. Cada fila guarda el id del modelo, la versión del prompt, la fecha y un hash del arameo del que se hizo; si ese texto cambia, la fila se descarta en la siguiente construcción. Las correcciones manuales van en data/translation_overrides.tsv y data/interpretation_overrides.tsv y sustituyen al texto del modelo. Cada traducción e interpretación tiene un enlace «Señalar un error».

**Estado.** Nada de esto lo han revisado especialistas. Lee las interpretaciones como una lectura informada, no como el veredicto de la tradición. Los prompts están en el repositorio (pipeline/translate.py, pipeline/interpret.py).

## Tablas

tables_version: `0.1.0`. [Lista completa de fuentes: data/SOURCES.md](../data/SOURCES.md)

## Exportaciones

- `https://zohar.digital/api/symbols.json`: todos los símbolos con sus recuentos (JSON)
- `https://zohar.digital/api/pairs.csv`: todos los pares de coocurrencia (CSV)
- `https://zohar.digital/api/meta.json`: metadatos de la compilación (JSON)

Por símbolo: todas las menciones en CSV (UTF-8 con BOM, se abre en Excel; la primera línea es un comentario, # tables_version=…, así que léela con pandas comment='#') o en JSON, p. ej. /api/symbol/moon.csv. Cada exportación incluye su tables_version.

## Citar

**BibTeX**

```
@misc{zohar_symbols_2026,
  author = {Fresco Benaim, Jose},
  title = {Zohar Symbols: a computed dictionary of the Zohar's kinnuyim},
  year = {2026},
  version = {0.1.0},
  url = {https://zohar.digital},
  doi = {10.5281/zenodo.23305097}
}
```

**Chicago**

```
Fresco Benaim, Jose. 2026. “Zohar Symbols: a computed dictionary of the Zohar's kinnuyim.” Versión 0.1.0. https://zohar.digital. https://doi.org/10.5281/zenodo.23305097.
```

**SBL**

```
Fresco Benaim, Jose. Zohar Symbols: a computed dictionary of the Zohar's kinnuyim. Versión 0.1.0. 2026. https://zohar.digital. https://doi.org/10.5281/zenodo.23305097.
```

## Advertencia

No somos especialistas. Queremos ofrecer una experiencia agradable del Zohar. Las traducciones y las glosas de los símbolos las produce Claude Fable, de Anthropic, y no han sido revisadas por especialistas.

## Licencias

Código: MIT. Texto y tablas: CC BY-SA 4.0, con atribución a Wikisource hebreo. Las obras citadas de Cordovero y Gikatilla son de dominio público; los resúmenes que este proyecto hace de ellas son CC BY-SA 4.0 como el resto de las tablas.
