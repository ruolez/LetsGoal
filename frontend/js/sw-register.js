/**
 * Service Worker Registration and PWA Utilities
 * Handles SW registration, updates, install prompts, and online/offline status
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    swPath: '/sw.js',
    swScope: '/',
    updateCheckInterval: 60 * 60 * 1000, // 1 hour
    installPromptDelay: 60 * 1000 // 60 seconds of use before showing prompt
  };

  // State
  let deferredInstallPrompt = null;
  let swRegistration = null;
  let updateBannerVisible = false;
  let installBannerVisible = false;
  let pageLoadTime = Date.now();

  // Initialize PWA features
  function init() {
    if ('serviceWorker' in navigator) {
      registerServiceWorker();
      setupOnlineOfflineHandlers();
      setupInstallPromptHandler();
      setupUpdateChecker();
    } else {
      console.log('[PWA] Service workers not supported');
    }
  }

  // Register service worker
  async function registerServiceWorker() {
    try {
      swRegistration = await navigator.serviceWorker.register(CONFIG.swPath, {
        scope: CONFIG.swScope
      });

      console.log('[PWA] Service worker registered:', swRegistration.scope);

      // Check for updates on registration
      swRegistration.addEventListener('updatefound', handleUpdateFound);

      // Handle controller change (new SW activated)
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        console.log('[PWA] New service worker activated');
      });

    } catch (error) {
      console.error('[PWA] Service worker registration failed:', error);
    }
  }

  // Handle service worker update found
  function handleUpdateFound() {
    const newWorker = swRegistration.installing;

    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        // New update available
        console.log('[PWA] Update available');
        showUpdateBanner();
      }
    });
  }

  // Show update available banner
  function showUpdateBanner() {
    if (updateBannerVisible) return;
    updateBannerVisible = true;

    const banner = createBanner({
      id: 'pwa-update-banner',
      message: 'A new version is available!',
      buttonText: 'Update',
      buttonAction: applyUpdate,
      bgColor: '#3b82f6', // Blue
      dismissible: true
    });

    document.body.appendChild(banner);
  }

  // Apply service worker update
  function applyUpdate() {
    if (swRegistration && swRegistration.waiting) {
      // Tell the waiting service worker to activate
      swRegistration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }

    // Reload to get the new version
    setTimeout(() => {
      window.location.reload();
    }, 100);
  }

  // Setup online/offline status handlers
  function setupOnlineOfflineHandlers() {
    let offlineBanner = null;

    window.addEventListener('online', () => {
      console.log('[PWA] Back online');
      if (offlineBanner) {
        offlineBanner.remove();
        offlineBanner = null;
      }
    });

    window.addEventListener('offline', () => {
      console.log('[PWA] Gone offline');
      if (!offlineBanner) {
        offlineBanner = createBanner({
          id: 'pwa-offline-banner',
          message: 'You are offline. Some features may be unavailable.',
          bgColor: '#f59e0b', // Yellow/Amber
          dismissible: false
        });
        document.body.appendChild(offlineBanner);
      }
    });

    // Check initial status
    if (!navigator.onLine) {
      const banner = createBanner({
        id: 'pwa-offline-banner',
        message: 'You are offline. Some features may be unavailable.',
        bgColor: '#f59e0b',
        dismissible: false
      });
      document.body.appendChild(banner);
    }
  }

  // Setup install prompt handler (A2HS - Add to Home Screen)
  function setupInstallPromptHandler() {
    window.addEventListener('beforeinstallprompt', (event) => {
      // Prevent the default browser prompt
      event.preventDefault();

      // Save the event for later use
      deferredInstallPrompt = event;

      console.log('[PWA] Install prompt available');

      // Show custom install banner after user has used the app for a while
      setTimeout(() => {
        if (deferredInstallPrompt && !installBannerVisible) {
          showInstallBanner();
        }
      }, CONFIG.installPromptDelay);
    });

    // Track when app is successfully installed
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App was installed');
      deferredInstallPrompt = null;
      hideInstallBanner();
    });
  }

  // Show install prompt banner
  function showInstallBanner() {
    if (installBannerVisible || !deferredInstallPrompt) return;
    installBannerVisible = true;

    const banner = createBanner({
      id: 'pwa-install-banner',
      message: 'Install Let\'s Goal for quick access!',
      buttonText: 'Install',
      buttonAction: promptInstall,
      bgColor: '#667eea', // Lotus gradient start
      dismissible: true,
      onDismiss: () => {
        installBannerVisible = false;
      }
    });

    document.body.appendChild(banner);
  }

  // Hide install banner
  function hideInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.remove();
    }
    installBannerVisible = false;
  }

  // Trigger the install prompt
  async function promptInstall() {
    if (!deferredInstallPrompt) {
      console.log('[PWA] No install prompt available');
      return;
    }

    // Show the browser's install prompt
    deferredInstallPrompt.prompt();

    // Wait for user's choice
    const { outcome } = await deferredInstallPrompt.userChoice;
    console.log('[PWA] User install choice:', outcome);

    // Clear the saved prompt
    deferredInstallPrompt = null;
    hideInstallBanner();
  }

  // Setup periodic update checks
  function setupUpdateChecker() {
    setInterval(async () => {
      if (swRegistration) {
        try {
          await swRegistration.update();
          console.log('[PWA] Checked for updates');
        } catch (error) {
          console.warn('[PWA] Update check failed:', error);
        }
      }
    }, CONFIG.updateCheckInterval);
  }

  // Create a notification banner
  function createBanner(options) {
    const {
      id,
      message,
      buttonText,
      buttonAction,
      bgColor = '#3b82f6',
      dismissible = false,
      onDismiss
    } = options;

    const banner = document.createElement('div');
    banner.id = id;
    banner.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      background: ${bgColor};
      color: white;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 500;
      z-index: 10000;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      animation: slideDown 0.3s ease-out;
    `;

    // Add animation keyframes if not already present
    if (!document.getElementById('pwa-banner-styles')) {
      const style = document.createElement('style');
      style.id = 'pwa-banner-styles';
      style.textContent = `
        @keyframes slideDown {
          from {
            transform: translateY(-100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `;
      document.head.appendChild(style);
    }

    // Message
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    banner.appendChild(messageSpan);

    // Action button
    if (buttonText && buttonAction) {
      const button = document.createElement('button');
      button.textContent = buttonText;
      button.style.cssText = `
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.4);
        color: white;
        padding: 6px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 600;
        transition: background 0.2s;
      `;
      button.addEventListener('mouseenter', () => {
        button.style.background = 'rgba(255, 255, 255, 0.3)';
      });
      button.addEventListener('mouseleave', () => {
        button.style.background = 'rgba(255, 255, 255, 0.2)';
      });
      button.addEventListener('click', () => {
        buttonAction();
        banner.remove();
      });
      banner.appendChild(button);
    }

    // Dismiss button
    if (dismissible) {
      const dismissBtn = document.createElement('button');
      dismissBtn.innerHTML = '&times;';
      dismissBtn.style.cssText = `
        background: transparent;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0 8px;
        line-height: 1;
        opacity: 0.8;
        transition: opacity 0.2s;
      `;
      dismissBtn.addEventListener('mouseenter', () => {
        dismissBtn.style.opacity = '1';
      });
      dismissBtn.addEventListener('mouseleave', () => {
        dismissBtn.style.opacity = '0.8';
      });
      dismissBtn.addEventListener('click', () => {
        banner.remove();
        if (onDismiss) onDismiss();
      });
      banner.appendChild(dismissBtn);
    }

    return banner;
  }

  // Public API for external access
  window.PWA = {
    // Check if app is installed (standalone mode)
    isInstalled: () => {
      return window.matchMedia('(display-mode: standalone)').matches ||
             window.navigator.standalone === true;
    },

    // Check if install prompt is available
    canInstall: () => {
      return deferredInstallPrompt !== null;
    },

    // Trigger install prompt programmatically
    promptInstall: promptInstall,

    // Check for updates
    checkForUpdates: async () => {
      if (swRegistration) {
        await swRegistration.update();
      }
    },

    // Clear all caches (for debugging)
    clearCaches: async () => {
      if (swRegistration && swRegistration.active) {
        swRegistration.active.postMessage({ type: 'CLEAR_CACHE' });
      }
    },

    // Get SW version
    getVersion: () => {
      return new Promise((resolve) => {
        if (swRegistration && swRegistration.active) {
          const channel = new MessageChannel();
          channel.port1.onmessage = (event) => {
            resolve(event.data.version);
          };
          swRegistration.active.postMessage(
            { type: 'GET_VERSION' },
            [channel.port2]
          );
        } else {
          resolve(null);
        }
      });
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
