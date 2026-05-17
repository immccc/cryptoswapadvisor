class SiteNav extends HTMLElement {
    connectedCallback() {
        const currentPath = window.location.pathname.split('/').pop() || 'index.html';
 
        this.innerHTML = `
        <nav class="nav">
            <div class="nav__inner">
                <a href="index.html"><img src="assets/images/logo.svg" alt="XXXXXXXXX" class="nav__logo"></a>
                <ul class="nav__links" id="nav-links">
                    <li class="nav__item"><a href="index.html" class="nav__link ${currentPath === 'index.html' ? 'nav__link--active' : ''}">Home</a></li>
                    <li class="nav__item"><a href="how-it-works.html" class="nav__link ${currentPath === 'how-it-works.html' ? 'nav__link--active' : ''}">Algorithm</a></li>
                    <li class="nav__item"><a href="backtests.html" class="nav__link ${currentPath === 'backtests.html' ? 'nav__link--active' : ''}">Backtesting</a></li>
                    <li class="nav__item"><a href="faq.html" class="nav__link ${currentPath === 'faq.html' ? 'nav__link--active' : ''}">FAQ</a></li>
                    <li class="nav__item"><a href="legal.html" class="nav__link ${currentPath === 'legal.html' ? 'nav__link--active' : ''}">Legal</a></li>
                    <li class="nav__item"><a href="join.html" class="nav__link nav__link--cta ${currentPath === 'join.html' ? 'nav__link--active' : ''}">Join!</a></li>
                </ul>
                <button class="nav__burger" id="nav-burger" aria-label="Toggle menu" aria-expanded="false">
                    <span class="nav__burger-line"></span>
                    <span class="nav__burger-line"></span>
                    <span class="nav__burger-line"></span>
                </button>
            </div>
        </nav>`;
 
        const burger = this.querySelector('#nav-burger');
        const links = this.querySelector('#nav-links');
 
        burger.addEventListener('click', () => {
            const isOpen = links.classList.toggle('nav__links--open');
            burger.classList.toggle('nav__burger--open', isOpen);
            burger.setAttribute('aria-expanded', isOpen);
        });
 
        // Close menu when a link is clicked
        links.querySelectorAll('.nav__link').forEach(link => {
            link.addEventListener('click', () => {
                links.classList.remove('nav__links--open');
                burger.classList.remove('nav__burger--open');
                burger.setAttribute('aria-expanded', false);
            });
        });
    }
}
 
customElements.define('site-nav', SiteNav);