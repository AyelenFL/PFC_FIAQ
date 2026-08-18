/**
 * Organización:
   1. Tema día/noche
   2. Partículas (tsParticles v2)
   3. Molécula que sigue al cursor (Anime.js)
   4. Formulario (fetch async)
   5. Termómetro (Anime.js)
 */

'use strict';

/*  
   1. TEMA DÍA / NOCHE
   El atributo data-theme en <html> controla todas las variables CSS.
   Se inicializa antes de DOMContentLoaded (inline en base.html)
   para evitar flash; acá solo se maneja el botón de toggle.
 */

function initThemeToggle() {
    /* Seleccionar ambos botones: desktop y mobile */
    const btns = [
        document.getElementById('theme-toggle'),
        document.getElementById('theme-toggle-mobile'),
    ].filter(Boolean); /* filter(Boolean) descarta los null si alguno no existe */
 
    if (!btns.length) return;
 
    /* Aplicar el mismo handler a ambos */
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next    = current === 'dark' ? 'light' : 'dark';
 
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('qfiaq_theme', next);
 
            /* Actualizar aria-label en ambos botones */
            btns.forEach(b => b.setAttribute(
                'aria-label',
                next === 'dark' ? 'Cambiar a modo día' : 'Cambiar a modo oscuro'
            ));
 
            reloadParticles();
        });
    });
}


/* 
   2. PARTÍCULAS — tsParticles v2

 */

/** Devuelve la config de tsParticles adaptada al tema actual */
function getParticlesConfig() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';

    return {
        
        background: { color: { value: 'transparent' } },

        fpsLimit: 60,
        detectRetina: true,

        interactivity: {
            events: {
                onHover: { enable: true, mode: 'repulse' },
                onClick: { enable: true, mode: 'push' },
                resize:  true,
            },
            modes: {
                repulse: { distance: 90,  duration: 0.4 },
                push:    { quantity: 2 },
            },
        },

        particles: {
            color: {
                /* Colores adaptativos al tema */
                value: isDark
                    ? ['#8A2BE2', '#a855f7', '#00C853', '#5532cc', '#33ff99']
                    : ['#6d21c8', '#8B5CF6', '#00a844', '#4a1baa', '#00cc6a'],
            },

            links: {
                /* El color de los enlaces también cambia con el tema */
                color:    isDark ? '#5532cc' : '#8B5CF6',
                distance: 140,
                enable:   true,
                opacity:  isDark ? 0.25 : 0.15,
                width:    1,
                triangles: {
                    enable:  true,
                    opacity: isDark ? 0.04 : 0.02,
                },
            },

            move: {
                direction: 'none',
                enable:    true,
                outModes:  { default: 'bounce' },
                random:    true,
                speed:     0.9,
                straight:  false,
            },

            number: {
                density: { enable: true, area: 900 },
                value:   70,
            },

            opacity: {
                value: { min: 0.15, max: isDark ? 0.55 : 0.35 },
                animation: { enable: true, speed: 0.7, minimumValue: 0.1 },
            },

            shape: { type: 'circle' },

            size: {
                value: { min: 1.5, max: 4 },
                animation: { enable: true, speed: 1.5, minimumValue: 0.5 },
            },
        },
    };
}

/** Carga o recarga tsParticles */
async function reloadParticles() {
    if (typeof tsParticles === 'undefined') {
        console.warn('[FIAQ] tsParticles no está disponible. Verificá el CDN en base.html.');
        return;
    }

    try {
        /* Destruir instancia previa si existe (evita duplicados al cambiar tema) */
        const container = tsParticles.dom().find(c => c.id === 'tsparticles');
        if (container) await container.destroy();

        await tsParticles.load('tsparticles', getParticlesConfig());
        console.log('[FIAQ] tsParticles cargado correctamente.');
    } catch (err) {
        console.error('[FIAQ] Error al cargar tsParticles:', err);
    }
}


/* 
   3. MOLÉCULA QUE SIGUE AL CURSOR
   Crea un SVG hexagonal en el DOM y lo mueve con Anime.js
   para un movimiento suave con lag (efecto "orbita").
   Solo activo en desktop (no en touch).
 */
function initCursorMolecule() {
    /* No activar en dispositivos táctiles */
    if (window.matchMedia('(hover: none)').matches) return;
 
    const wrapper = document.createElement('div');
    wrapper.id = 'cursor-molecule';
    /* Estilos inline: position fixed, sin pointer-events, centrado en 0,0 */
    wrapper.style.cssText = `
        position: fixed;
        top: 0; left: 0;
        width: 44px; height: 44px;
        pointer-events: none;
        z-index: 9999;
        opacity: 0;
        will-change: transform;
    `;
 
    const mol = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    mol.setAttribute('viewBox', '0 0 44 44');
    mol.setAttribute('width',  '44');
    mol.setAttribute('height', '44');
    mol.setAttribute('xmlns',  'http://www.w3.org/2000/svg');
    mol.setAttribute('aria-hidden', 'true');
    mol.style.display = 'block';
 
    mol.innerHTML = `
        <g>
            <line x1="22" y1="22" x2="8"  y2="10" stroke="#8A2BE2" stroke-width="1.3" stroke-linecap="round"/>
            <line x1="22" y1="22" x2="36" y2="10" stroke="#8A2BE2" stroke-width="1.3" stroke-linecap="round"/>
            <line x1="22" y1="22" x2="22" y2="37" stroke="#00C853" stroke-width="1.3" stroke-linecap="round"/>
            <line x1="22" y1="22" x2="6"  y2="28" stroke="#a855f7" stroke-width="1"   stroke-linecap="round"/>
            <circle cx="22" cy="22" r="5"   fill="#8A2BE2" opacity="0.92"/>
            <circle cx="8"  cy="10" r="2.8" fill="#a855f7" opacity="0.85"/>
            <circle cx="36" cy="10" r="3.2" fill="#00C853" opacity="0.85"/>
            <circle cx="22" cy="37" r="2.5" fill="#a855f7" opacity="0.75"/>
            <circle cx="6"  cy="28" r="2"   fill="#00C853" opacity="0.7"/>
        </g>
    `;
 
    wrapper.appendChild(mol);
    document.body.appendChild(wrapper);
 
    /* Posición objetivo (mouse real) y posición suavizada actual */
    let targetX = -100; /* empieza fuera de pantalla */
    let targetY = -100;
    let currentX = -100;
    let currentY = -100;
    let visible  = false;
 
    /* Factor de suavizado: cuanto menor, más lag */
    const EASE = 0.12;
 
    /* Mostrar/ocultar al entrar/salir del main */
    const mainEl = document.querySelector('.main-content');
    if (mainEl) {
        mainEl.addEventListener('mouseenter', () => {
            visible = true;
            wrapper.style.opacity = '0.82';
        });
        mainEl.addEventListener('mouseleave', () => {
            visible = false;
            wrapper.style.opacity = '0';
        });
    }
 
    /* Actualizar la posición objetivo con cada movimiento del mouse */
    document.addEventListener('mousemove', (e) => {
        targetX = e.clientX;
        targetY = e.clientY;
    });
 
    /* RAF: actualiza la posición actual con interpolación (lag suave)
     */
    function tick() {
        currentX += (targetX - currentX) * EASE;
        currentY += (targetY - currentY) * EASE;
 
        /* Centrar el wrapper en el cursor (44/2 = 22px de offset) */
        wrapper.style.left = (currentX - 22) + 'px';
        wrapper.style.top  = (currentY - 22) + 'px';
 
        requestAnimationFrame(tick);
    }
    tick();
 
    /* Rotación continua del SVG con Anime.js; sobre el SVG, no el wrapper*/
    anime({
        targets:  mol,          /* rota el SVG interno, no el wrapper */
        rotate:   '1turn',
        duration: 9000,
        easing:   'linear',
        loop:     true,
    });
}


/*  
   4. FORMULARIO DE PREDICCIÓN
   - Limpia el label al hacer submit
   - Muestra "La capacidad antioxidante de (molécula) es: X"
   - Dispara la animación del termómetro
*/

function initForm() {
    const form            = document.getElementById('prediction-form');
    const smilesInput     = document.getElementById('smiles-input');
    const submitBtn       = document.getElementById('submit-button');
    const resultContainer = document.getElementById('result-container');
    const spinner         = document.getElementById('spinner');
    const exampleBtn      = document.getElementById('example-btn');

    if (!form) return;

    /* Botón de ejemplo */
    if (exampleBtn) {
        exampleBtn.addEventListener('click', () => {
            smilesInput.value = 'CC(=O)Oc1ccccc1C(=O)O'; /* Aspirina */
            smilesInput.focus();
        });
    }

    /* Estado de carga */
    const setLoading = (loading) => {
        submitBtn.disabled    = loading;
        smilesInput.disabled  = loading;
        if (spinner) spinner.classList.toggle('hidden', !loading);
        submitBtn.querySelector('.btn-text').textContent = loading ? 'Analizando…' : 'Predecir';
    };

    /* Mostrar mensaje de error */
    const showError = (msg) => {
        resultContainer.innerHTML = `
            <div class="error-message" role="alert">
                <span aria-hidden="true">⚠</span>
                <span>${msg}</span>
            </div>`;
    };

    /*
     * Configuración de clases del modelo.
     Mapea class_id -> { ícono, color CSS, adjetivo para la oración }
     Ajustar si el handler cambia los valores numéricos.
        0 = Baja   -> rojo
        1 = Media  -> amarillo
       2 = Alta   -> verde
     */
    const CLASS_CONFIG = {
        0: { icon: '🔴', color: 'var(--class-low)',  label: 'Baja'  },
        1: { icon: '🟡', color: 'var(--class-mid)',  label: 'Media' },
        2: { icon: '🟢', color: 'var(--class-high)', label: 'Alta'  },
    };

    /* Mostrar resultado con clase + confianza */
    const showSuccess = (smiles, classId, predictionText, confidence) => {
        const cfg = CLASS_CONFIG[classId] ?? { icon: '◈', color: 'var(--green)', label: predictionText };
 
        resultContainer.innerHTML = `
            <div class="success-message success-message--class-${classId}">
                <div class="result-badge">
                    <span class="result-badge__icon">${cfg.icon}</span>
                    <span class="result-badge__label" style="color:${cfg.color}">${cfg.label}</span>
                </div>
                <p class="result-sentence">
                    <span class="result-molecule-name">${smiles}</span>
                    tiene una
                    <span class="result-class-word" style="color:${cfg.color}">${cfg.label.toLowerCase()} capacidad antioxidante</span>.
                </p>
                <div class="result-confidence">
                    <span class="result-confidence__label">Confianza del modelo</span>
                    <div class="result-confidence__bar-wrap">
                        <div class="result-confidence__bar" id="confidence-bar" style="width:0%; background:${cfg.color}"></div>
                    </div>
                    <span class="result-confidence__pct" id="confidence-pct">0%</span>
                </div>
            </div>`;
 
        /* Animar entrada del bloque */
        anime({
            targets:    '#result-container .success-message',
            opacity:    [0, 1],
            translateY: [12, 0],
            duration:   450,
            easing:     'easeOutQuart',
        });
 
        /* Animar barra de confianza y número */
        anime({
            targets:  { val: 0 },
            val:      confidence,
            duration: 900,
            delay:    200,
            easing:   'easeOutCubic',
            update: function(anim) {
                const v = Math.round(anim.animations[0].currentValue);
                const bar = document.getElementById('confidence-bar');
                const pct = document.getElementById('confidence-pct');
                if (bar) bar.style.width = v + '%';
                if (pct) pct.textContent  = v + '%';
            },
        });
    };
 
    /*  Submit */
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
 
        const inputValue = smilesInput.value.trim();
 
        if (!inputValue) {
            showError('Por favor, ingresá una molécula en un formato válido (SMILES, nombre en inglés, CAS).');
            return;
        }
 
        /* Guardar el SMILES antes de limpiar el campo */
        const smilesForDisplay = inputValue;
 
        /* Limpiar campo y resultado anterior */
        smilesInput.value = '';
        resultContainer.innerHTML = `<p class="info-message">⟳ Analizando molécula…</p>`;
 
        setLoading(true);
 
        try {
            const response = await fetch('/predict', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ molecule_input: smilesForDisplay }),
            });
 
            const data = await response.json();
 
            if (response.ok && data.prediction !== undefined) {
                /* data.prediction  -> texto, ej: "Alta Capacidad Antioxidante"
                   data.class_id    -> número: 0, 1 ó 2
                   data.confidence  -> porcentaje: 0-100 */
                showSuccess(
                    smilesForDisplay,
                    data.class_id,
                    data.prediction,
                    data.confidence ?? 0
                );
 
                /* Actualizar el termómetro con clase + confianza */
                updateThermometer(data.class_id, data.confidence ?? 0);
 
            } else {
                showError(data.error || `Error del servidor (${response.status}).`);
            }
 
        } catch (netErr) {
            console.error('[FIAQ] Error de red:', netErr);
            showError('No se pudo conectar con el servidor. Verificá tu conexión.');
        } finally {
            setLoading(false);
        }
    });
    
}


/* 
   5. TERMÓMETRO
   Recibe class_id (0=Baja, 1=Media, 2=Alta) y confidence (0-100).
     El tubo se divide en 3 zonas iguales de 80px cada una:
       Zona Baja  -> y: 220..260  (fondo del tubo)
       Zona Media -> y: 140..220  (medio)
       Zona Alta  -> y:  20..140  (tope)
 
   */
 
/* Límites de cada zona en coordenadas del viewBox (de abajo hacia arriba) */
const THERMO_ZONES = [
    { classId: 0, yBottom: 260, yTop: 180, color: '#FF1744' }, /* Baja  */
    { classId: 1, yBottom: 180, yTop: 100, color: '#FFD600' }, /* Media */
    { classId: 2, yBottom: 100, yTop:  20, color: '#00C853' }, /* Alta  */
];
 
const THERMO_LABELS = {
    0: { text: 'Baja',  color: '#FF5252' },
    1: { text: 'Media', color: '#FFD600' },
    2: { text: 'Alta',  color: '#00C853' },
};
 
function updateThermometer(classId, confidence) {
    const panel    = document.getElementById('thermometer-panel');
    const fillClip = document.getElementById('thermo-fill-clip');
    const indicator= document.getElementById('thermo-indicator');
    const levelEl  = document.getElementById('thermo-label');
 
    if (!panel || !fillClip) return;
 
    const zone = THERMO_ZONES[classId] ?? THERMO_ZONES[1];
    const zoneH = zone.yBottom - zone.yTop;          /* altura de la zona en viewBox px */
 
    /*
     El relleno cubre:
       - TODAS las zonas inferiores (completas)
       - La zona actual hasta el % de confianza
     
      Ejemplo: clase Alta (2), confianza 70%
        -> Llena zona Baja completa (80px) + zona Media completa (80px)
          + 70% de zona Alta (56px)
        -> fillTop = 100 - (80*0.70) = 44   ->  y del clip = 44
     */
    const confidenceRatio  = Math.max(0, Math.min(100, confidence)) / 100;
    const fillInsideZone   = zoneH * confidenceRatio;
    const fillTop          = zone.yBottom - fillInsideZone;
 
    /* Mostrar panel */
    if (panel.classList.contains('hidden')) panel.classList.remove('hidden');
 
    /* Animar entrada del panel */
    anime({
        targets:    '#thermometer-panel',
        opacity:    [0, 1],
        translateX: [28, 0],
        duration:   600,
        easing:     'easeOutQuart',
    });
 
    /* Posición Y anterior del clip (para animar desde ahí) */
    const prevY = parseFloat(fillClip.getAttribute('y') || 260);
 
    /* Animar relleno */
    anime({
        targets:  { y: prevY },
        y:        fillTop,
        duration: 1100,
        easing:   'easeOutElastic(1, 0.55)',
        update: function(anim) {
            const currentTop = anim.animations[0].currentValue;
            const h = 260 - currentTop + 40; /* +40 cubre el bulbo */
            fillClip.setAttribute('y',      currentTop);
            fillClip.setAttribute('height', Math.max(0, h));
        },
    });
 
    /* Animar indicador (triángulo) a la posición del nivel */
    const indicatorY = fillTop;
    const prevPoints = indicator.getAttribute('points') || `24,260 14,255 14,265`;
    anime({
        targets:  indicator,
        opacity:  [0, 1],
        points: [
            { value: prevPoints },
            { value: `24,${indicatorY} 14,${indicatorY - 5} 14,${indicatorY + 5}` },
        ],
        duration: 1100,
        easing:   'easeOutElastic(1, 0.55)',
    });
 
    /* Etiqueta textual */
    const lbl = THERMO_LABELS[classId] ?? THERMO_LABELS[1];
    if (levelEl) {
        levelEl.textContent = lbl.text;
        levelEl.style.color = lbl.color;
    }
}


/* 
   INICIALIZACIÓN
   ÚNICO DOMContentLoaded que llama a todas las funciones.
*/

document.addEventListener('DOMContentLoaded', () => {

    initThemeToggle();    /* 1. Botón día/noche */
    reloadParticles();    /* 2. Partículas */
    initCursorMolecule(); /* 3. Molécula del cursor */
    initForm();           /* 4. Formulario + resultado */
    /* El termómetro (5) se llama desde showSuccess dentro de initForm */

    console.log('[FIAQ] App inicializada correctamente.');
});



/* MENÚ HAMBURGUESA MOBILE
   Maneja la apertura/cierre del menú mobile
   - Alterna las clases .is-open en el botón y en el menú
   - Actualiza aria-expanded y aria-hidden para accesibilidad
   - Cierra el menú al hacer click en un link interno
   - Cierra el menú al presionar Escape
   - Cierra el menú al hacer resize a desktop
 */
 
(function initMobileMenu() {
    const btn       = document.getElementById('mobile-menu-btn');
    const menu      = document.getElementById('mobile-menu');
    const links     = menu ? menu.querySelectorAll('.mobile-menu__link') : [];
 
    if (!btn || !menu) return;
 
    /* Abrir / cerrar al click en el hexágono */
    btn.addEventListener('click', () => {
        const isOpen = btn.classList.contains('is-open');
 
        btn.classList.toggle('is-open');
        menu.classList.toggle('is-open');
 
        /* Actualizar atributos de accesibilidad */
        btn.setAttribute('aria-expanded', String(!isOpen));
        menu.setAttribute('aria-hidden',  String(isOpen));
        btn.setAttribute('aria-label', isOpen ? 'Abrir menú' : 'Cerrar menú');
    });
 
    /* Cerrar al hacer click en cualquier link del menú */
    links.forEach(link => {
        link.addEventListener('click', () => {
            btn.classList.remove('is-open');
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
            menu.setAttribute('aria-hidden',  'true');
            btn.setAttribute('aria-label', 'Abrir menú');
        });
    });
 
    /* Cerrar al presionar Escape */
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && btn.classList.contains('is-open')) {
            btn.classList.remove('is-open');
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
            menu.setAttribute('aria-hidden',  'true');
            btn.setAttribute('aria-label', 'Abrir menú');
            btn.focus();
        }
    });
 
    /* Cerrar si el usuario agranda la ventana a desktop */
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && btn.classList.contains('is-open')) {
            btn.classList.remove('is-open');
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
            menu.setAttribute('aria-hidden',  'true');
        }
    }, { passive: true });
 
})();