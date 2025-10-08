(function () {
  const revealElements = document.querySelectorAll('.reveal');
  if (revealElements.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );
    revealElements.forEach((element) => observer.observe(element));
  }

  const menuToggle = document.querySelector('[data-menu-toggle]');
  const menuContainer = document.querySelector('[data-menu]');
  if (menuToggle && menuContainer) {
    menuToggle.addEventListener('click', () => {
      const isOpen = menuContainer.classList.toggle('is-open');
      menuToggle.setAttribute('aria-expanded', String(isOpen));
      if (!isOpen) {
        menuContainer.querySelectorAll('.menu-item-has-children.is-open')
          .forEach((item) => item.classList.remove('is-open'));
      }
    });

    const submenuLinks = Array.from(menuContainer.querySelectorAll('.menu-item-has-children > a'));
    submenuLinks.forEach((link) => {
      link.addEventListener('click', (event) => {
        const parent = link.parentElement;
        if (!(parent instanceof HTMLElement)) {
          return;
        }
        const isMobile = window.matchMedia('(max-width: 960px)').matches;
        if (!isMobile) {
          return;
        }
        if (!parent.classList.contains('is-open')) {
          event.preventDefault();
          Array.from(parent.parentElement?.children || [])
            .forEach((sibling) => sibling !== parent && sibling.classList?.remove('is-open'));
          parent.classList.add('is-open');
        }
      });
    });

    Array.from(menuContainer.querySelectorAll('a')).forEach((link) => {
      link.addEventListener('click', () => {
        if (!window.matchMedia('(max-width: 960px)').matches) {
          return;
        }
        const parent = link.parentElement;
        if (parent && parent.classList.contains('menu-item-has-children') && !parent.classList.contains('is-open')) {
          return;
        }
        menuContainer.classList.remove('is-open');
        menuContainer.querySelectorAll('.menu-item-has-children.is-open')
          .forEach((item) => item.classList.remove('is-open'));
        menuToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  const heroDataElement = document.getElementById('hero-banner-data');
  const heroSection = document.querySelector('[data-hero-rotator]');
  if (heroSection && heroDataElement) {
    let sequences = [];
    try {
      sequences = JSON.parse(heroDataElement.textContent || '[]') || [];
    } catch (error) {
      console.warn('hero data parse error', error);
    }
    sequences = Array.isArray(sequences) ? sequences.filter((item) => item && item.title && item.description) : [];

    const backgroundEl = heroSection.querySelector('[data-hero-background]');
    const titleEl = heroSection.querySelector('[data-hero-title]');
    const textEl = heroSection.querySelector('[data-hero-text]');
    const transitions = ['fade', 'slide', 'zoom', 'lift'];
    let currentIndex = 0;
    let cleanupTimer;

    const setContent = (sequence) => {
      if (titleEl && sequence?.title) {
        titleEl.textContent = sequence.title;
      }
      if (textEl && sequence?.description) {
        textEl.textContent = sequence.description;
      }
    };

    const applyTransition = (transition) => {
      heroSection.classList.remove('transition-fade', 'transition-slide', 'transition-zoom', 'transition-lift', 'is-transitioning');
      void heroSection.offsetWidth;
      heroSection.classList.add('is-transitioning', `transition-${transition}`);
      if (cleanupTimer) {
        window.clearTimeout(cleanupTimer);
      }
      cleanupTimer = window.setTimeout(() => {
        heroSection.classList.remove('is-transitioning', `transition-${transition}`);
      }, 900);
    };

    const updateBackground = (imageUrl) => {
      if (!backgroundEl || !imageUrl) {
        return;
      }
      const fallbackTimer = window.setTimeout(() => {
        backgroundEl.style.backgroundImage = `url('${imageUrl}')`;
        backgroundEl.classList.remove('is-fading');
      }, 650);
      const handleTransitionEnd = (event) => {
        if (event.propertyName !== 'opacity') {
          return;
        }
        window.clearTimeout(fallbackTimer);
        backgroundEl.removeEventListener('transitionend', handleTransitionEnd);
        backgroundEl.style.backgroundImage = `url('${imageUrl}')`;
        requestAnimationFrame(() => {
          backgroundEl.classList.remove('is-fading');
        });
      };
      backgroundEl.addEventListener('transitionend', handleTransitionEnd, { once: true });
      backgroundEl.classList.add('is-fading');
    };

    const showSequence = (index, { immediate = false } = {}) => {
      const sequence = sequences[index];
      if (!sequence) {
        return;
      }
      if (immediate) {
        setContent(sequence);
        if (backgroundEl && sequence.image) {
          backgroundEl.style.backgroundImage = `url('${sequence.image}')`;
        }
        return;
      }
      const transition = transitions[Math.floor(Math.random() * transitions.length)] || 'fade';
      applyTransition(transition);
      setContent(sequence);
      if (sequence.image) {
        updateBackground(sequence.image);
      }
    };

    if (sequences.length) {
      showSequence(0, { immediate: true });
    }

    if (sequences.length > 1) {
      window.setInterval(() => {
        currentIndex = (currentIndex + 1) % sequences.length;
        showSequence(currentIndex);
      }, 9000);
    }
  }

  const searchField = document.querySelector('#product-search');
  const cards = Array.from(document.querySelectorAll('[data-product-name]'));
  const counter = document.querySelector('.filter-counter');

  const updateCounter = (visible) => {
    if (!counter) {
      return;
    }
    counter.textContent = `${visible} de ${cards.length} itens`;
  };

  if (searchField && cards.length) {
    searchField.addEventListener('input', (event) => {
      const term = String(event.target.value || '').trim().toLowerCase();
      let visible = 0;
      cards.forEach((card) => {
        const name = card.getAttribute('data-product-name') || '';
        const category = card.getAttribute('data-product-category') || '';
        const matches = !term || name.includes(term) || category.includes(term);
        card.style.display = matches ? '' : 'none';
        if (matches) {
          visible += 1;
        }
      });
      updateCounter(visible);
    });
    updateCounter(cards.length);
  }

  const renderAssistantRichText = (text, links) => {
    const fragment = document.createDocumentFragment();
    const safeText = String(text || '');
    if (!safeText.trim()) {
      return fragment;
    }
    const lines = safeText.split(/\n/);
    let listEl = null;
    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        listEl = null;
        return;
      }
      if (/^[-•]/.test(trimmed)) {
        if (!listEl) {
          listEl = document.createElement('ul');
          fragment.appendChild(listEl);
        }
        const li = document.createElement('li');
        li.textContent = trimmed.replace(/^[-•]\s*/, '');
        listEl.appendChild(li);
        return;
      }
      listEl = null;
      if (/^próximos passos[:]?/i.test(trimmed)) {
        const heading = document.createElement('span');
        heading.className = 'assistant-heading';
        heading.textContent = trimmed.replace(/:$/, '');
        fragment.appendChild(heading);
        return;
      }
      const paragraph = document.createElement('p');
      paragraph.textContent = trimmed;
      fragment.appendChild(paragraph);
    });

    if (Array.isArray(links) && links.length) {
      const linkList = document.createElement('ul');
      linkList.className = 'assistant-links';
      links.forEach((item) => {
        if (!item || !item.url) {
          return;
        }
        const li = document.createElement('li');
        const anchor = document.createElement('a');
        anchor.href = item.url;
        anchor.textContent = item.title || item.url;
        anchor.target = '_blank';
        anchor.rel = 'noopener';
        li.appendChild(anchor);
        linkList.appendChild(li);
      });
      if (linkList.children.length) {
        fragment.appendChild(linkList);
      }
    }

    return fragment;
  };

  const assistantContainer = document.querySelector('[data-assistant-container]');
  const assistantToggle = document.querySelector('[data-assistant-toggle]');
  if (assistantContainer) {
    const widget = assistantContainer.querySelector('[data-role="assistant-widget"]');
    const messagesContainer = assistantContainer.querySelector('[data-role="assistant-messages"]');
    const form = assistantContainer.querySelector('[data-role="assistant-form"]');
    const statusElement = assistantContainer.querySelector('[data-role="assistant-status"]');
    const defaultGreeting = widget?.dataset.assistantGreeting || '';
    let assistantMode = widget?.dataset.assistantMode === 'authenticated' ? 'api' : 'public';
    let historyLoaded = false;

    const appendMessage = (text, role, options = {}) => {
      if (!messagesContainer) {
        return;
      }
      const wrapper = document.createElement('div');
      wrapper.className = `assistant-message ${role === 'bot' ? 'from-assistant' : 'from-user'}`;
      const bubble = document.createElement('div');
      bubble.className = 'assistant-bubble';
      if (role === 'bot') {
        bubble.appendChild(renderAssistantRichText(text, options.links));
      } else {
        bubble.textContent = text;
      }
      wrapper.appendChild(bubble);
      messagesContainer.appendChild(wrapper);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    const renderSnapshot = (snapshot) => {
      if (!messagesContainer) {
        return;
      }
      const messages = Array.isArray(snapshot?.messages) ? snapshot.messages : [];
      messagesContainer.innerHTML = '';
      if (!messages.length && defaultGreeting) {
        appendMessage(defaultGreeting, 'bot');
        return;
      }
      messages.forEach((item) => {
        const text = typeof item?.content === 'string' ? item.content : '';
        const role = item?.role === 'assistant' ? 'bot' : 'user';
        appendMessage(text, role, { links: item?.links });
      });
    };

    const syncConversation = async () => {
      if (!messagesContainer) {
        return;
      }
      try {
        if (statusElement) {
          statusElement.textContent = 'Sincronizando histórico...';
        }
        const response = await fetch('/api/assistant/conversation', {
          method: 'GET',
          credentials: 'same-origin',
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) {
          if (response.status === 401) {
            widget.dataset.assistantMode = 'public';
            assistantMode = 'public';
            return;
          }
          throw new Error(`Falha ao buscar histórico (${response.status})`);
        }
        const payload = await response.json();
        renderSnapshot(payload);
        widget.dataset.assistantMode = 'authenticated';
        assistantMode = 'api';
        historyLoaded = true;
      } catch (error) {
        console.warn('assistant history unavailable', error);
      } finally {
        if (statusElement) {
          statusElement.textContent = '';
        }
      }
    };

    const ensureHistory = () => {
      if (!historyLoaded && assistantMode === 'api') {
        syncConversation();
      }
    };

    const openAssistant = () => {
      if (assistantContainer.classList.contains('is-open')) {
        return;
      }
      assistantContainer.classList.add('is-open');
      assistantContainer.setAttribute('aria-hidden', 'false');
      if (assistantToggle) {
        assistantToggle.setAttribute('aria-expanded', 'true');
      }
      ensureHistory();
      if (!historyLoaded && defaultGreeting) {
        appendMessage(defaultGreeting, 'bot');
      }
    };

    const closeAssistant = () => {
      assistantContainer.classList.remove('is-open');
      assistantContainer.setAttribute('aria-hidden', 'true');
      if (assistantToggle) {
        assistantToggle.setAttribute('aria-expanded', 'false');
      }
    };

    if (assistantToggle) {
      assistantToggle.addEventListener('click', () => {
        if (assistantContainer.classList.contains('is-open')) {
          closeAssistant();
        } else {
          openAssistant();
        }
      });
    }

    const closeButton = assistantContainer.querySelector('[data-assistant-close]');
    if (closeButton) {
      closeButton.addEventListener('click', () => closeAssistant());
    }

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && assistantContainer.classList.contains('is-open')) {
        closeAssistant();
      }
    });

    document.addEventListener('click', (event) => {
      if (!assistantContainer.classList.contains('is-open')) {
        return;
      }
      if (!assistantContainer.contains(event.target) && event.target !== assistantToggle) {
        closeAssistant();
      }
    });

    if (form && messagesContainer) {
      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        const message = String(formData.get('message') || '').trim();
        if (!message) {
          return;
        }
        appendMessage(message, 'user');
        form.reset();

        if (statusElement) {
          statusElement.textContent = 'Consultando o assistente...';
        }

        const sendViaApi = async () => {
          try {
            const response = await fetch('/api/assistant/message', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
              },
              credentials: 'same-origin',
              body: JSON.stringify({ message }),
            });
            if (response.status === 401) {
              assistantMode = 'public';
              widget.dataset.assistantMode = 'public';
              return false;
            }
            if (!response.ok) {
              throw new Error(`Falha ao conversar com o assistente (${response.status})`);
            }
            const payload = await response.json();
            const messages = Array.isArray(payload?.messages) ? payload.messages : [];
            const lastAssistant = [...messages].reverse().find((item) => item?.role === 'assistant');
            if (lastAssistant) {
              appendMessage(lastAssistant.content || '', 'bot', { links: lastAssistant.links });
              return true;
            }
            appendMessage('Assistente respondeu, mas não foi possível exibir a mensagem agora.', 'bot');
            return true;
          } catch (error) {
            console.error(error);
            appendMessage('Houve um problema ao falar com o assistente técnico. Tente novamente mais tarde.', 'bot');
            return true;
          }
        };

        const sendViaFallback = async () => {
          try {
            const response = await fetch('/assistente/ask', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({ message }),
            });
            if (!response.ok) {
              throw new Error(`Erro ${response.status}`);
            }
            const payload = await response.json();
            appendMessage(
              payload.reply || 'Não consegui consultar o assistente agora. Tente novamente mais tarde.',
              'bot',
              { links: payload.links }
            );
          } catch (error) {
            console.error(error);
            appendMessage('Houve um problema na consulta. Nossa equipe pode ajudar pelo WhatsApp ou e-mail.', 'bot');
          }
          return true;
        };

        try {
          if (!(assistantMode === 'api' && await sendViaApi())) {
            await sendViaFallback();
          }
        } finally {
          if (statusElement) {
            statusElement.textContent = '';
          }
        }
      });
    }
  }
})();
