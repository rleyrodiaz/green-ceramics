// ── Estado ────────────────────────────────────────────────────────
let todosLosProductos = [];
let filtros = {
    categoria: "",
    tecnica: "",
    stock: "",
    buscar: "",
};

// ── Cargar productos ──────────────────────────────────────────────
async function cargarProductos() {
    try {
        const res = await fetch("/api/productos");
        todosLosProductos = await res.json();
        renderProductos();
    } catch (e) {
        console.error("Error cargando productos:", e);
        document.getElementById("products-grid").innerHTML =
            "<p style='color:var(--text-muted)'>Error cargando productos.</p>";
    }
}

// ── Cargar categorías ─────────────────────────────────────────────
async function cargarCategorias() {
    try {
        const res = await fetch("/api/categorias");
        const cats = await res.json();
        const lista = document.getElementById("filtro-categorias");
        cats.forEach(cat => {
            const li = document.createElement("li");
            li.className = "filtro-item";
            li.dataset.value = cat.slug;
            li.textContent = cat.nombre;
            li.addEventListener("click", () => setFiltroCategoria(cat.slug, li));
            lista.appendChild(li);
        });
    } catch (e) {
        console.error("Error cargando categorías:", e);
    }
}

// ── Filtros ───────────────────────────────────────────────────────
function setFiltroCategoria(valor, el) {
    filtros.categoria = valor;
    document.querySelectorAll("#filtro-categorias .filtro-item")
        .forEach(i => i.classList.remove("active"));
    el.classList.add("active");
    renderProductos();
}

function aplicarFiltros(productos) {
    return productos.filter(p => {
        if (filtros.categoria && p.categoria_slug !== filtros.categoria) return false;
        if (filtros.tecnica && p.tecnica !== filtros.tecnica) return false;
        if (filtros.buscar && !p.nombre.toLowerCase().includes(filtros.buscar.toLowerCase())) return false;
        if (filtros.stock === "disponible" && p.stock === 0) return false;
        if (filtros.stock === "ultimas" && p.stock > 3) return false;
        return true;
    });
}

// ── Render ────────────────────────────────────────────────────────
function renderProductos() {
    const grid = document.getElementById("products-grid");
    const count = document.getElementById("catalogo-count");
    const filtrados = aplicarFiltros(todosLosProductos);

    count.textContent = `${filtrados.length} ${filtrados.length === 1 ? "pieza" : "piezas"}`;

    if (filtrados.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1; padding:4rem 0; text-align:center; color:var(--text-muted)">
                No hay piezas que coincidan con los filtros.
            </div>`;
        return;
    }

    grid.innerHTML = filtrados.map(p => {
        const precio = `$${p.precio.toLocaleString("es-AR")}`;
        const stockClass = p.stock === 0 ? "no-stock" : p.stock <= 3 ? "low-stock" : "in-stock";
        const stockText = p.stock === 0 ? "Sin stock" : p.stock <= 3 ? `Últimas ${p.stock}` : "Disponible";

        //aca Las imágenes que ves ahora son placeholder de internet — vienen de un servicio llamado 
        // picsum.photos que genera fotos aleatorias. Las estamos usando porque los productos del seed 
        // no tienen imágenes cargadas en Cloudinary todavía.
        // Significa

        // Si el producto tiene imagen en la DB → la muestra
        // Si no tiene → genera una foto aleatoria de picsum usando el slug como semilla

        // Cuando cargues productos reales desde el panel admin con sus fotos subidas a Cloudinary, p.imagen va a tener la URL real y picsum desaparece solo.
        // El flujo real será:
        // Admin sube foto → va a Cloudinary → URL se guarda en DB → 
        // API la devuelve en p.imagen → se muestra en el catálogo

        const imagen = p.imagen || `https://picsum.photos/seed/${p.slug}/400/530`;
        const tag = p.categoria || p.tecnica || "Cerámica";

        return `
            <div class="product-card" onclick="window.location='/producto/${p.slug}'">
                <div class="product-img">
                    <img src="${imagen}" alt="${p.nombre}" loading="lazy">
                    <div class="product-tag">${tag}</div>
                    <div class="stock-badge ${stockClass}" style="
                        position:absolute; bottom:1rem; right:1rem;
                        background:rgba(245,240,232,0.92);
                        padding:0.3rem 0.7rem;
                        font-size:0.7rem;
                        letter-spacing:0.1em;
                    ">${stockText}</div>
                </div>
                <div class="product-info">
                    <h3 class="product-name">${p.nombre}</h3>
                    <p class="product-desc">${p.descripcion || ""}</p>
                    <div class="product-footer">
                        <span class="product-price">${precio}</span>
                        <button class="btn-pedido"
                            onclick="event.stopPropagation(); addToCart(${JSON.stringify(p).replace(/"/g, '&quot;')})"
                            ${p.stock === 0 ? "disabled style='opacity:0.4;cursor:not-allowed'" : ""}>
                            ${p.stock === 0 ? "Sin stock" : "Agregar"}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

// ── Filtros click ─────────────────────────────────────────────────
document.querySelectorAll(".filtro-item[data-tecnica]").forEach(el => {
    el.addEventListener("click", () => {
        document.querySelectorAll("[data-tecnica]").forEach(i => i.classList.remove("active"));
        el.classList.add("active");
        filtros.tecnica = el.dataset.tecnica;
        renderProductos();
    });
});

document.querySelectorAll(".filtro-item[data-stock]").forEach(el => {
    el.addEventListener("click", () => {
        document.querySelectorAll("[data-stock]").forEach(i => i.classList.remove("active"));
        el.classList.add("active");
        filtros.stock = el.dataset.stock;
        renderProductos();
    });
});

// ── Búsqueda ──────────────────────────────────────────────────────
let searchTimer;
document.getElementById("catalogo-search").addEventListener("input", e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        filtros.buscar = e.target.value;
        renderProductos();
    }, 300);
});

// ── Init ──────────────────────────────────────────────────────────
cargarCategorias();
cargarProductos();
updateCartCount();