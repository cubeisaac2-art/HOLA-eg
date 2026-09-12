document.addEventListener('DOMContentLoaded', () => {
    const toggleTheme = document.getElementById('themeToggle');
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.dataset.theme = savedTheme;

    if (toggleTheme) {
        toggleTheme.addEventListener('click', () => {
            const nextTheme = document.body.dataset.theme === 'dark' ? 'light' : 'dark';
            document.body.dataset.theme = nextTheme;
            localStorage.setItem('theme', nextTheme);
        });
    }

    document.querySelectorAll('.favorite-toggle').forEach((button) => {
        button.addEventListener('click', async () => {
            const contentType = button.dataset.contentType;
            const contentId = button.dataset.contentId;
            const response = await fetch(`/favorite/${contentType}/${contentId}`, { method: 'POST' });
            const payload = await response.json().catch(() => ({ status: 'error' }));

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (payload.status === 'added') {
                button.textContent = 'Quitar favorito';
                button.classList.add('active');
                return;
            }

            if (payload.status === 'removed') {
                button.textContent = 'Añadir favorito';
                button.classList.remove('active');
            }
        });
    });

    document.querySelectorAll('[data-share-title]').forEach((button) => {
        button.addEventListener('click', async () => {
            const title = button.dataset.shareTitle;
            const url = button.dataset.shareUrl || window.location.href;
            const shareData = { title, text: title, url };

            try {
                if (navigator.share) {
                    await navigator.share(shareData);
                    return;
                }
                await navigator.clipboard.writeText(url);
                button.innerHTML = '<i class="bi bi-check2 me-1"></i>Enlace copiado';
                window.setTimeout(() => {
                    button.innerHTML = '<i class="bi bi-share me-1"></i>Compartir';
                }, 2200);
            } catch (error) {
                if (error.name !== 'AbortError') {
                    window.open(`https://wa.me/?text=${encodeURIComponent(`${title} ${url}`)}`, '_blank', 'noopener');
                }
            }
        });
    });

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/js/sw.js').catch((error) => {
                console.error('Service worker registration failed:', error);
            });
        });
    }

    const installButton = document.getElementById('installPwaBtn');
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (event) => {
        event.preventDefault();
        deferredPrompt = event;
        if (installButton) {
            installButton.style.display = 'inline';
        }
    });

    if (installButton) {
        installButton.addEventListener('click', async () => {
            if (!deferredPrompt) {
                return;
            }
            deferredPrompt.prompt();
            const result = await deferredPrompt.userChoice;
            console.log('PWA install choice:', result.outcome);
            deferredPrompt = null;
        });
    }
});
