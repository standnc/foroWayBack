/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./forum/templates/**/*.html",
    // forum/forms.py define clases Tailwind dentro de los widgets; sin esto,
    // el purgado se llevaría los estilos de todos los formularios.
    "./forum/forms.py",
  ],
  theme: {
    extend: {
      // ── Nota importante ──────────────────────────────────────────────────
      // Aquí NO van los colores boom/coral/gold/retro que había en el <script>
      // inline de base.html. Aquella config nunca llegó a aplicarse: se asignaba
      // a `tailwind = {...}` ANTES de cargar el CDN, y el script del CDN crea su
      // propio window.tailwind al inicializarse, descartándola. Verificado en
      // producción con navegador: .bg-boom era transparente y .font-display no
      // daba Fredoka.
      //
      // Definirlos ahora activaría de golpe las decenas de `text-boom`,
      // `bg-boom` y `font-display` repartidas por las plantillas y CAMBIARÍA el
      // diseño. El aspecto actual lo sostienen las clases estándar más el
      // bloque de paleta de static/src/input.css.
      //
      // Adoptarlos es una decisión de diseño aparte, con capturas antes/después
      // (scripts/capturar_visual.py). Ver todos.md 3.7.
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
};
