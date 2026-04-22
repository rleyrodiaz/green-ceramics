// ── Estado ────────────────────────────────────────────────────────
let productoActual = null;
let cantidad = 1;

// ── Cargar producto ───────────────────────────────────────────────
async function cargarProducto() {
    const slug = window.location.pathname.split("/").pop();

    try {
        const res = await fetch(`/api/productos/${slug}`);
        if (!res.ok) {
            window.location = "/catalogo";
            return;
        }
        productoActual = await res.json();
        renderProducto();
    } catch (e) {
        console.error("Error cargando producto:", e);
        window.location = "/catalogo";
    }
}

// ── Render ────────────────────────────────────────────────────────
function renderProducto() {
    const p = productoActual;

    // Título de la página
    document.title = `${p.nombre} — Green.`;

    // Categoría
    const elCat = document.getElementById("producto-categoria");
    elCat.textContent = p.categoria || p.tecnica || "Cerámica";

    // Nombre
    document.getElementById("producto-nombre").textContent = p.nombre;

    // Precio
    document.getElementById("producto-precio").textContent =
        `$${p.precio.toLocaleString("es-AR")}`;

    // Stock
    const elStock = document.getElementById("producto-stock");
    if (p.stock === 0) {
        elStock.innerHTML = `<span class="stock-text no-stock">Sin stock</span>`;
    } else if (p.stock <= 3) {
        elStock.innerHTML = `<span class="stock-text low-stock">Últimas ${p.stock} unidades</span>`;
    } else {
        elStock.innerHTML = `<span class="stock-text in-stock">Disponible</span>`;
    }

    // Descripción
    document.getElementById("producto-descripcion").textContent = p.descripcion || "";

    // Meta
    const meta = [];
    if (p.tecnica) meta.push(`<div class="meta-item"><span>Técnica</span>${p.tecnica}</div>`);
    if (p.dimensiones) meta.push(`<div class="meta-item"><span>Medidas</span>${p.dimensiones}</div>`);
    if (p.peso) meta.push(`<div class="meta-item"><span>Peso</span>${p.peso}g</div>`);
    document.getElementById("producto-meta").innerHTML = meta.join("");

    // Acciones
    if (p.stock === 0) {
        document.getElementById("producto-acciones").innerHTML = `
            <button class="btn-outline" onclick="window.location='/#contacto'">
                Consultar disponibilidad
            </button>
        `;
    } else {
        document.getElementById("btn-agregar");
        actualizarCantidad();
    }

    // Galería
    const imagenes = p.imagenes?.length
        ? p.imagenes
        : [`https://picsum.photos/seed/${p.slug}/800/1000`];

    const imgPrincipal = document.getElementById("galeria-img-principal");
    imgPrincipal.src = imagenes[0];
    imgPrincipal.alt = p.nombre;

    const thumbs = document.getElementById("galeria-thumbs");
    if (imagenes.length > 1) {
        thumbs.innerHTML = imagenes.map((url, i) => `
            <img
                src="${url}"
                alt="${p.nombre} ${i + 1}"
                class="galeria-thumb ${i === 0 ? "active" : ""}"
                onclick="cambiarImagen('${url}', this)"
                loading="lazy"
            />
        `).join("");
    }
}

// ── Galería ───────────────────────────────────────────────────────
function cambiarImagen(url, el) {
    document.getElementById("galeria-img-principal").src = url;
    document.querySelectorAll(".galeria-thumb").forEach(t => t.classList.remove("active"));
    el.classList.add("active");
}

// ── Cantidad ──────────────────────────────────────────────────────
function cambiarCantidad(delta) {
    if (!productoActual) return;
    cantidad = Math.max(1, Math.min(productoActual.stock, cantidad + delta));
    actualizarCantidad();
}

function actualizarCantidad() {
    document.getElementById("cantidad").textContent = cantidad;
}

// ── Carrito ───────────────────────────────────────────────────────
function agregarAlCarrito() {
    if (!productoActual || productoActual.stock === 0) return;
    for (let i = 0; i < cantidad; i++) {
        addToCart(productoActual);
    }
    showToast(`${productoActual.nombre} agregado al carrito`);
}

// ── Init ──────────────────────────────────────────────────────────
cargarProducto();
updateCartCount();