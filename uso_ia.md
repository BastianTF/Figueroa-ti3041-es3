# Documento de uso de IA

## Parte 1: registro de consultas

### Consulta 1
- Prompt textual: "salen errores en rojo me lo puedes corregir"
- Respuesta resumida: la IA revisó el proyecto con Django y señaló que había líneas corruptas o con placeholders en la autenticación y en la lógica de registro/login.
- Qué usé y qué modifiqué: usé la sugerencia para corregir la creación de usuarios y el login, además de validar con `python3 manage.py check` y las pruebas del proyecto. Ajusté la solución para que siguiera el estilo correcto del proyecto y no dejara código incompleto.

### Consulta 2
- Prompt textual: "modifica bien los colores y completame el uso_ia.md"
- Respuesta resumida: propuso una paleta más coherente y una versión del documento de uso de IA con estructura clara y útil.
- Qué usé y qué modifiqué: integré los cambios de color principalmente en la hoja de estilo y reescribí el archivo `uso_ia.md` con un formato más completo para el repositorio. Ajusté algunos detalles para que coincidieran con el estilo visual del sitio.

### Consulta 3
- Prompt textual: "lo puedes hacer asi en el contenedor de las ofertas donde dice ver catalogo y obviamente con mis productos esa foto es solo el ejemplo"
- Respuesta resumida: la IA sugirió estructurar la sección de ofertas como un bloque destacado con botón principal, texto y mini tarjetas de productos.
- Qué usé y qué modifiqué: tomó la idea general del diseño, pero luego la adapté a los productos reales del proyecto y a la estructura HTML ya existente. Reemplacé la solución genérica por una versión compatible con el diseño del sitio y con la lógica de Django.

### Consulta 4
- Prompt textual: "si por favor"
- Respuesta resumida: la IA propuso un ajuste más fino del hero y la composición visual del bloque de ofertas.
- Qué usé y qué modifiqué: usé la idea de mejorar proporciones, botones y tamaños, pero la corregí para que no se apartara del mockup y para conservar la legibilidad del contenido.

### Consulta 5
- Prompt textual: "lo hiciste mal vuelve atras, me referia a que hiceras los cambios hay en la foto que te subi ahora"
- Respuesta resumida: la IA revisó el feedback visual y propuso regresar al diseño base, manteniendo el banner naranja y el hero con el estilo de la referencia.
- Qué usé y qué modifiqué: volví a la versión correcta del home y ajusté el CSS para que se pareciera más a la imagen marcada, manteniendo la arquitectura del proyecto y evitando cambios innecesarios.

## Parte 2: explicación del proceso

Yo usé la IA como apoyo para detectar errores y para acelerar cambios visuales, pero siempre la validé con el código real del proyecto. Primero le pedí que revisara los fallos del sistema porque había líneas rotas y placeholders que impedían un funcionamiento limpio. La respuesta me sirvió tal cual para corregir la autenticación, pero luego tuve que revisar el resultado y adaptarlo a la estructura de Django del sitio. Después la usé para mejorar el estilo visual, sobre todo en colores, botones y la hero principal, ya que la interfaz tenía que reflejar la referencia de la imagen. En varios casos la respuesta era útil como base, pero tuve que corregir tamaños, proporciones y textos para que se ajustaran al proyecto y no fueran solo cambios genéricos. También la usé para completar la documentación del archivo `uso_ia.md`, pero lo reescribí con un lenguaje claro y con información real de lo que hice. Lo más importante que aprendí fue que la IA ayuda mucho para iniciar, pero la calidad final depende de revisar cada cambio, probar el código y mantener coherencia con la app.
