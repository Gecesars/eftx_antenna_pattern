(function () {
  function onReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback, { once: true });
    } else {
      callback();
    }
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function formatTime(isoString) {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      if (Number.isNaN(date.getTime())) {
        return '';
      }
      return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch (error) {
      console.warn('Assistant time format error', error);
      return '';
    }
  }

  function fetchJson(url, options) {
    return fetch(url, options).then((response) => {
      if (response.ok) {
        return response.json();
      }
      return response
        .json()
        .catch(() => ({}))
        .then((payload) => {
          const message = payload.message || payload.error || 'Erro inesperado.';
          const error = new Error(message);
          error.status = response.status;
          throw error;
        });
    });
  }

  onReady(() => {
    const panel = document.getElementById('assistant-panel');
    const toggle = document.getElementById('assistant-toggle');
    if (!panel || !toggle) {
      return;
    }

    const closeBtn = panel.querySelector('[data-role="close"]');
    const messagesContainer = panel.querySelector('[data-role="messages"]');
    const statusEl = panel.querySelector('[data-role="status"]');
    const form = panel.querySelector('[data-role="form"]');
    const textarea = panel.querySelector('textarea[name="message"]');
    const sendBtn = panel.querySelector('[data-role="send"]');

    const fetchUrl = panel.dataset.fetchUrl;
    const postUrl = panel.dataset.postUrl;
    if (!fetchUrl || !postUrl) {
      console.warn('Assistant endpoints nao configurados.');
      return;
    }

    let isOpen = false;
    let isLoading = false;
    let hasLoaded = false;

    function setStatus(message, type) {
      if (!statusEl) return;
      statusEl.textContent = message || '';
      statusEl.classList.toggle('error', type === 'error');
    }

    function setLoading(state) {
      isLoading = state;
      panel.classList.toggle('is-loading', state);
      if (sendBtn) {
        sendBtn.disabled = state;
      }
      if (textarea) {
        textarea.readOnly = state;
      }
    }

    function renderMessages(messages) {
      if (!messagesContainer) return;
      messagesContainer.innerHTML = '';
      messages.forEach((message) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'assistant-message ' + (message.role === 'assistant' ? 'from-assistant' : 'from-user');

        const bubble = document.createElement('div');
        bubble.className = 'assistant-bubble';
        bubble.textContent = message.content || '';
        wrapper.appendChild(bubble);

        if (message.created_at) {
          const meta = document.createElement('span');
          meta.className = 'assistant-meta';
          meta.textContent = formatTime(message.created_at);
          wrapper.appendChild(meta);
        }

        messagesContainer.appendChild(wrapper);
      });
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function togglePanel(force) {
      const nextState = typeof force === 'boolean' ? force : !isOpen;
      if (nextState === isOpen) {
        return;
      }
      isOpen = nextState;
      panel.classList.toggle('is-open', isOpen);
      toggle.setAttribute('aria-expanded', String(isOpen));
      if (isOpen) {
        if (!hasLoaded) {
          loadHistory();
        }
        if (textarea) {
          textarea.focus({ preventScroll: false });
        }
      }
    }

    function loadHistory() {
      if (isLoading) return;
      setLoading(true);
      setStatus('Carregando historico...');
      fetchJson(fetchUrl, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      })
        .then((data) => {
          const messages = Array.isArray(data.messages) ? data.messages : [];
          renderMessages(messages);
          setStatus(messages.length ? '' : 'Pronto para ajudar.');
          hasLoaded = true;
        })
        .catch((error) => {
          console.warn('Assistant history error', error);
          setStatus('Nao foi possivel carregar o historico agora.', 'error');
        })
        .finally(() => setLoading(false));
    }

    function sendMessage(content) {
      if (isLoading || !content) {
        return;
      }
      setLoading(true);
      setStatus('Consultando assistente...');
      fetchJson(postUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'X-CSRFToken': getCookie('csrf_token') || '',
        },
        body: JSON.stringify({ message: content }),
      })
        .then((data) => {
          const messages = Array.isArray(data.messages) ? data.messages : [];
          renderMessages(messages);
          if (textarea) {
            textarea.value = '';
            textarea.focus({ preventScroll: false });
          }
          setStatus('');
        })
        .catch((error) => {
          console.warn('Assistant send error', error);
          setStatus(error.message || 'Falha ao falar com o assistente.', 'error');
        })
        .finally(() => setLoading(false));
    }

    toggle.addEventListener('click', () => togglePanel());
    if (closeBtn) {
      closeBtn.addEventListener('click', () => togglePanel(false));
    }

    if (form && textarea) {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        const value = textarea.value.trim();
        if (!value) {
          setStatus('Digite uma pergunta para continuar.');
          return;
        }
        sendMessage(value);
      });
    }

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && isOpen) {
        togglePanel(false);
      }
    });
  });
})();

