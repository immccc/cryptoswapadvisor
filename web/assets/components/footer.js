class Footer extends HTMLElement {
    connectedCallback() {
        const currentPath = window.location.pathname.split('/').pop() || 'index.html';
        
        this.innerHTML = `
        <footer class="footer">
            <div>
                <p>
                    Created by <a href="https://github.com/xxxxxxx" target="_blank" rel="noopener noreferrer">xxxxxxx</a>. 
                    &copy; 2026 All rights reserved.
                </p>
            </div>
        </footer>
        `;
    }
}

customElements.define('site-footer', Footer);