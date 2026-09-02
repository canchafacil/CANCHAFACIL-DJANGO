// static/js/theme.js
(function() {
    'use strict';
    
    const STORAGE_KEY = 'canchafacil_theme';
    const DARK_THEME = 'dark';
    const LIGHT_THEME = 'light';
    
    // Aplicar tema inmediatamente para evitar parpadeo
    function applyThemeImmediately() {
        const storedTheme = localStorage.getItem(STORAGE_KEY);
        if (storedTheme) {
            document.documentElement.setAttribute('data-bs-theme', storedTheme);
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-bs-theme', DARK_THEME);
        } else {
            document.documentElement.setAttribute('data-bs-theme', LIGHT_THEME);
        }
    }
    
    // Ejecutar inmediatamente
    applyThemeImmediately();
    
    // Cuando el DOM esté listo
    document.addEventListener('DOMContentLoaded', function() {
        const toggleButton = document.getElementById('themeToggle');
        
        if (!toggleButton) return;
        
        const themeIcon = toggleButton.querySelector('i');
        
        function updateToggleButton(theme) {
            if (theme === DARK_THEME) {
                themeIcon.className = 'bi bi-sun';
                toggleButton.setAttribute('title', 'Cambiar a modo claro');
                toggleButton.innerHTML = '<i class="bi bi-sun"></i>';
            } else {
                themeIcon.className = 'bi bi-moon-stars';
                toggleButton.setAttribute('title', 'Cambiar a modo oscuro');
                toggleButton.innerHTML = '<i class="bi bi-moon-stars"></i>';
            }
        }
        
        function setTheme(theme) {
            document.documentElement.setAttribute('data-bs-theme', theme);
            localStorage.setItem(STORAGE_KEY, theme);
            updateToggleButton(theme);
            
            // Disparar evento personalizado para otros scripts
            document.dispatchEvent(new CustomEvent('themeChanged', { 
                detail: { theme: theme } 
            }));
        }
        
        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === DARK_THEME ? LIGHT_THEME : DARK_THEME;
            setTheme(newTheme);
        }
        
        // Inicializar botón
        const currentTheme = document.documentElement.getAttribute('data-bs-theme') || LIGHT_THEME;
        updateToggleButton(currentTheme);
        
        // Event listener para el botón
        toggleButton.addEventListener('click', toggleTheme);
        
        // Escuchar cambios del sistema
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
            // Solo actualizar si no hay preferencia guardada
            if (!localStorage.getItem(STORAGE_KEY)) {
                setTheme(event.matches ? DARK_THEME : LIGHT_THEME);
            }
        });
    });
})();