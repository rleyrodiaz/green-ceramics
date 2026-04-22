// ── Auth admin ────────────────────────────────────────────────────
function verificarAdmin() {
    const token = localStorage.getItem("admin_token");
    if (!token) {
        window.location = "/admin";
        return null;
    }
    return token;
}

function logout() {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_user");
    window.location = "/admin";
}

// ── API helper ────────────────────────────────────────────────────
async function apiAdmin(url, method = "GET", body = null) {
    const token = localStorage.getItem("admin_token");
    if (!token) { window.location = "/admin"; return null; }

    const opts = {
        method,
        headers: {
            "Authorization": `Bearer ${token}`,
            ...(body ? { "Content-Type": "application/json" } : {}),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
    };

    try {
        const res = await fetch(url, opts);
        if (res.status === 403) { window.location = "/admin"; return null; }
        return await res.json();
    } catch (e) {
        console.error("API error:", e);
        return null;
    }
}

// ── Helpers compartidos ───────────────────────────────────────────
async function cargarCategoriaSelect() {
    const select = document.getElementById("p-categoria");
    if (!select) return;
    try {
        const res = await fetch("/api/categorias");
        const cats = await res.json();
        select.innerHTML = `<option value="">Sin categoría</option>` +
            cats.map(c => `<option value="${c.id}">${c.nombre}</option>`).join("");
    } catch (e) {
        console.error("Error cargando categorías:", e);
    }
}

// function cerrarModal(id) {
//     document.getElementById(id).classList.remove("active");
//     document.body.style.overflow = "";
// }

function cerrarModal(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove("active");
        el.style.display = "none";
    }
    document.body.style.overflow = "";
}



// ── Ver producto (modal) ───────────────────────────────────────────
// let productosCache = [];
window.productosCache = [];

function verProducto(slug) {
    console.log("verProducto llamado con slug:", slug);
    // const p = productosCache.find(x => x.slug === slug);
    const p = window.productosCache.find(x => x.slug === slug);
    console.log("producto encontrado:", p);
    if (!p) return;

    const imagen = p.imagen || `https://picsum.photos/seed/${p.slug}/400/530`;
    document.getElementById("ver-imagen").src = imagen;
    document.getElementById("ver-nombre").textContent = p.nombre;
    document.getElementById("ver-precio").textContent = `$${p.precio.toLocaleString("es-AR")}`;
    document.getElementById("ver-categoria").textContent = p.categoria || "Cerámica";
    document.getElementById("ver-descripcion").textContent = p.descripcion || "";
    document.getElementById("ver-link-publico").href = `/producto/${p.slug}`;

    const stockEl = document.getElementById("ver-stock");
    if (p.stock === 0) {
        stockEl.innerHTML = `<span style="color:#A32D2D;font-size:0.8rem;
                              letter-spacing:0.1em;text-transform:uppercase">Sin stock</span>`;
    } else if (p.stock <= 3) {
        stockEl.innerHTML = `<span style="color:var(--clay);font-size:0.8rem;
                              letter-spacing:0.1em;text-transform:uppercase">
                              Últimas ${p.stock} unidades</span>`;
    } else {
        stockEl.innerHTML = `<span style="color:var(--sage);font-size:0.8rem;
                              letter-spacing:0.1em;text-transform:uppercase">Disponible</span>`;
    }

    const meta = [];
    if (p.tecnica) meta.push(`<div><span style="color:var(--clay)">Técnica</span> — ${p.tecnica}</div>`);
    if (p.dimensiones) meta.push(`<div><span style="color:var(--clay)">Medidas</span> — ${p.dimensiones}</div>`);
    document.getElementById("ver-meta").innerHTML = meta.join("");

    // document.getElementById("modal-ver-producto").classList.add("active");
    document.getElementById("modal-ver-producto").style.display = "flex";
    document.body.style.overflow = "hidden";
}

// ── Editar producto ───────────────────────────────────────────────
async function editarProducto(slug) {
    console.log("editarProducto llamado con slug:", slug);
    console.log("productosCache:", window.productosCache);
    const p = window.productosCache.find(x => x.slug === slug);
    console.log("producto encontrado:", p);
    if (!p) return;
    console.log("modal existe:", document.getElementById("modal-editar-producto"));
    console.log("editar-nombre existe:", document.getElementById("editar-nombre"));

    const resCats = await fetch("/api/categorias");
    const cats = await resCats.json();
    const selectCat = document.getElementById("editar-categoria");
    selectCat.innerHTML = `<option value="">Sin categoría</option>` +
        cats.map(c => `<option value="${c.id}"
            ${c.nombre === p.categoria ? "selected" : ""}>${c.nombre}</option>`
        ).join("");

    document.getElementById("editar-id").value = p.id;
    document.getElementById("editar-titulo").textContent = p.nombre;
    document.getElementById("editar-nombre").value = p.nombre;
    document.getElementById("editar-precio").value = p.precio;
    document.getElementById("editar-desc").value = p.descripcion || "";
    document.getElementById("editar-stock").value = p.stock;
    document.getElementById("editar-dimensiones").value = p.dimensiones || "";
    document.getElementById("editar-peso").value = p.peso || "";
    document.getElementById("editar-destacado").checked = p.destacado;
    document.getElementById("editar-tecnica").value = p.tecnica || "";

    document.getElementById("editar-error").style.display = "none";
    document.getElementById("editar-success").style.display = "none";
    // document.getElementById("modal-editar-producto").classList.add("active");
    document.getElementById("modal-editar-producto").style.display = "flex";
    document.body.style.overflow = "hidden";
}

async function guardarEdicion() {
    const id = document.getElementById("editar-id").value;
    const nombre = document.getElementById("editar-nombre").value.trim();
    const precio = document.getElementById("editar-precio").value;
    const errEl = document.getElementById("editar-error");

    if (!nombre || !precio) {
        errEl.textContent = "Nombre y precio son obligatorios.";
        errEl.style.display = "block";
        return;
    }

    const body = {
        name: nombre,
        price: parseFloat(precio),
        description: document.getElementById("editar-desc").value,
        stock: parseInt(document.getElementById("editar-stock").value),
        dimensions: document.getElementById("editar-dimensiones").value,
        weight_grams: parseInt(document.getElementById("editar-peso").value) || null,
        is_featured: document.getElementById("editar-destacado").checked,
        technique: document.getElementById("editar-tecnica").value || null,
    };

    const result = await apiAdmin(`/api/admin/productos/${id}`, "PUT", body);

    if (!result) {
        errEl.textContent = "Error al guardar los cambios.";
        errEl.style.display = "block";
        return;
    }

    document.getElementById("editar-success").style.display = "block";
    errEl.style.display = "none";

    setTimeout(() => {
        cerrarModal("modal-editar-producto");
        cargarTablaProductos();
    }, 1500);
}

