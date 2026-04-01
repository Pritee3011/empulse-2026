
document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-btn');
    const sideNav = document.getElementById('side-nav');
    const backdrop = document.getElementById('menu-backdrop');
    const dynamicBg = document.getElementById('dynamic-bg');
    const navLinks = document.querySelectorAll('.vintage-nav-links a');

    // Use the variable passed from HTML or fallback to a string
    const defaultBgUrl = typeof DEFAULT_BG !== 'undefined' ? DEFAULT_BG : '/static/images/MPULSE.png';

    // Function to open menu
    const openMenu = () => {
        sideNav.classList.add('open');
        backdrop.classList.add('active');
    };

    // Function to close menu and reset background
    const closeMenu = () => {
        sideNav.classList.remove('open');
        backdrop.classList.remove('active');
        
        // Reset to clear main logo
        dynamicBg.style.backgroundImage = `url('${defaultBgUrl}')`;
        dynamicBg.classList.add('crystal-clear');
    };

    // Event Listeners
    if(menuBtn) menuBtn.addEventListener('click', openMenu);
    if(closeBtn) closeBtn.addEventListener('click', closeMenu);
    if(backdrop) backdrop.addEventListener('click', closeMenu);

    // Hover logic for background images
    navLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            const newBg = this.getAttribute('data-bg');
            if(newBg) {
                // Prepend slash if missing to ensure absolute path
                const path = newBg.startsWith('/') ? newBg : `/${newBg}`;
                dynamicBg.style.backgroundImage = `url('${path}')`;
                
                // Remove crystal-clear to allow vintage filters/blend modes from style.css
                dynamicBg.classList.remove('crystal-clear');
            }
        });
    });
});