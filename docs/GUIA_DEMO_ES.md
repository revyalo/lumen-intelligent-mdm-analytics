# Abrir y presentar Lumen

La plataforma está implementada en Python y funciona en tu ordenador. No necesita cuenta, API ni servicios de pago. Los datos y la identidad Lumen son nuevos y ficticios.

## Abrir

En macOS, abre **Start Lumen.command** desde la carpeta del proyecto. El lanzador utiliza el entorno .venv de esta carpeta o un intérprete activo con la aplicación instalada; si no encuentra uno, instala las dependencias en `.venv`. También puedes seguir los cuatro comandos de instalación del README. La primera instalación necesita conexión para descargar paquetes.

Una vez iniciado Streamlit, abre la dirección local que aparezca. La aplicación genera los datos a partir de la semilla elegida: no necesitas preparar un servidor de base de datos. Para detenerla, usa Ctrl+C en la terminal del lanzador.

## Recorrido de 8–10 minutos

1. **Overview:** explica ingresos, actividad y concentración. Aclara que la fecha de referencia es 30/09/2026 y los datos son sintéticos. Cambia región o periodo y observa los valores recalculados.
2. **Data Explorer:** selecciona `order_lines` en la barra lateral, filtra una cantidad y descarga los registros. Un pedido puede contener varias líneas: no confundas sus denominadores.
3. **Exploratory Analysis:** muestra distribución, boxplot, estadística y correlación. Compara IQR con z-score; los pedidos grandes pueden ser legítimos.
4. **Data Quality:** selecciona `customer_sources`. Compara antes/después, departamentos y auditoría. Los emails inválidos pasan a ausentes: la completitud puede bajar aunque la validez mejore.
5. **Business Intelligence:** abre SQL Lab y ejecuta `monthly_sales`. Explica CTE, agregación temporal y LAG; después muestra RFM. Frecuencia significa pedidos distintos, no líneas.
6. **Entity Resolution:** revisa una pareja sin conflicto. Escribe un nombre de revisor y un motivo; acepta y observa la trazabilidad. Revoca la decisión y comprueba que los originales siguen disponibles. Las revisiones quedan en `runtime/reviews.sqlite`, excluido de Git.
7. **Machine Learning:** explica por qué se usan R/F/M, log1p y escalado; muestra selección de K, perfiles y tabla cruzada con RFM. En anomalías, selecciona `order_lines` y compara algoritmos. Las anomalías no son automáticamente errores o fraude.
8. **Reports:** genera el informe ZIP y abre su `report.html`. Incluye resultados, evidencia, método, límites y acciones posibles. Consulta también `docs/VALIDATION.md` para los experimentos realmente ejecutados.

## Datasets externos

El cargador de CSV admite exploración, calidad e informes sobre tablas arbitrarias. Conserva una descarga de los bytes originales. Si una columna de fecha tiene valores inválidos se mantiene como texto para revisarla. Para MDM, el CSV debe contener `record_id` único y `name`; claves fiscales, emails o SKU aportan evidencias adicionales. BI y clustering necesitan el modelo relacional del diccionario, disponible a través del cargador de bundles de Python. No se atribuyen KPIs comerciales a un CSV sin relaciones suficientes.

## Estado real

Están disponibles las ocho secciones y los módulos reutilizables, las pruebas, dos notebooks ejecutados y los experimentos en dos tamaños y dos semillas. Embeddings es una extensión opcional, sin modelo descargado ni evaluación inventada. No hay predicción de demanda. La aplicación es una demostración local para un analista; no incluye autenticación multiusuario ni despliegue empresarial. El workflow de GitHub está preparado y todavía no ha corrido en GitHub. Se ha creado un repositorio privado vacío de preparación, sin push. Revisa RELEASE_AUDIT.md antes de aprobar la subida privada y espera al resultado de CI antes de valorar hacer el repositorio público.


## Ampliación local: Operational Time Analytics

Abre la novena sección en la navegación. La demo inicial calcula 2 horas de uso, 50% de utilización (horario explícito 08:00–12:00), máximo de 3 personas y 6 parejas. Activa capacidad 2 para ver 25 minutos de sobreocupación. Los datos son ficticios.

Prueba **Identity mapping demo** y activa **Apply reviewed identity map** para comparar identidades antes/después. En **Validation challenge**, los errores impiden calcular hasta que autorices excluir filas en cuarentena. **Multi-day synthetic** muestra el mapa por días/horas. Los filtros de empleados cambian la población analizada. Exporta el ZIP desde **Export → Build operational evidence report**.

Esta ampliación permanece en una rama local; la versión del paquete sigue siendo 0.1.0. Consulta [contratos, algoritmos, experimentos y límites](operational_time/README.md) y [comprobación de entrega](operational_time/DELIVERY.md).
