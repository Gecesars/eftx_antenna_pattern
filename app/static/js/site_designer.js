(function () {
  const stateRoot = document.querySelector('[data-site-designer]');
  if (!stateRoot) {
    return;
  }

  const menuButtons = Array.from(stateRoot.querySelectorAll('[data-section]'));
  const editorContainer = stateRoot.querySelector('[data-editor]');
  const statusElement = stateRoot.querySelector('[data-status]');
  const previewContainer = stateRoot.querySelector('[data-preview-container]');
  const previewFrame = stateRoot.querySelector('[data-preview]');
  const refreshButton = stateRoot.querySelector('[data-action="refresh"]');
  const reloadPreviewButton = stateRoot.querySelector('[data-action="reload-preview"]');
  const toggleDeviceButton = stateRoot.querySelector('[data-action="toggle-device"]');
  const deviceLabel = stateRoot.querySelector('[data-device-label]');

  let siteState = window.SITE_DESIGNER_STATE || {};
  let currentSection = 'contacts';
  let previewDevice = (previewContainer && previewContainer.getAttribute('data-device')) || 'desktop';

  const endpoints = {
    contacts: '/admin/site-designer/contacts',
    heroPromos: '/admin/site-designer/hero/promos',
    heroImages: '/admin/site-designer/hero/images',
    highlights: '/admin/site-designer/highlights',
    gallery: '/admin/site-designer/gallery',
    faq: '/admin/site-designer/faq',
    uploadImage: '/admin/site-designer/upload/image',
    uploadDocument: '/admin/site-designer/upload/document',
    documentsUpsert: '/admin/site-designer/documents',
  };

  function csrfToken() {
    return siteState.csrf_token || '';
  }

  function showStatus(message, type = 'info') {
    if (!statusElement) {
      return;
    }
    statusElement.textContent = message || '';
    statusElement.classList.remove('is-error');
    if (type === 'error') {
      statusElement.classList.add('is-error');
    }
  }

  function handleResponse(response) {
    if (!response.ok) {
      return response.json().catch(() => ({})).then((data) => {
        const errorMessage = data.message || data.error || response.statusText || 'Erro inesperado';
        throw new Error(errorMessage);
      });
    }
    return response.json();
  }

  function postJSON(url, payload) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
      },
      body: JSON.stringify(payload),
    }).then(handleResponse);
  }

  function deleteRequest(url) {
    return fetch(url, {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrfToken(),
      },
    }).then(handleResponse);
  }

  function postForm(url, formData) {
    if (!formData.get('csrf_token')) {
      formData.append('csrf_token', csrfToken());
    }
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
    }).then(handleResponse);
  }

  function setState(nextState) {
    if (!nextState) {
      return;
    }
    siteState = nextState;
    showStatus('Alterações sincronizadas com sucesso.');
    renderSection(currentSection);
    updateDeviceView(previewDevice);
  }

  function refreshState() {
    return fetch('/admin/site-designer/state', {
      credentials: 'same-origin',
    })
      .then(handleResponse)
      .then((data) => {
        setState(data);
        reloadPreview();
      })
      .catch((error) => {
        showStatus(error.message, 'error');
      });
  }

  function reloadPreview() {
    if (!previewFrame) {
      return;
    }
    const currentSrc = previewFrame.getAttribute('src');
    const base = currentSrc ? currentSrc.split('?')[0] : window.location.href;
    previewFrame.setAttribute('src', `${base}?t=${Date.now()}`);
  }

  function updateDeviceView(mode) {
    previewDevice = mode;
    if (!previewContainer) {
      return;
    }
    previewContainer.setAttribute('data-device', mode);
    if (deviceLabel) {
      deviceLabel.textContent = mode === 'desktop' ? 'Ver como celular' : 'Ver como desktop';
    }
  }

  function valueOrEmpty(value) {
    return value == null ? '' : value;
  }

  function renderSection(section) {
    currentSection = section;
    menuButtons.forEach((button) => {
      button.classList.toggle('is-active', button.dataset.section === section);
    });
    if (!editorContainer) {
      return;
    }
    switch (section) {
      case 'contacts':
        renderContacts();
        break;
      case 'hero':
        renderHero();
        break;
      case 'highlights':
        renderHighlights();
        break;
      case 'gallery':
        renderGallery();
        break;
      case 'faq':
        renderFaq();
        break;
      case 'documents':
        renderDocuments();
        break;
      default:
        editorContainer.innerHTML = '<p>Selecione uma área para começar a editar.</p>';
        break;
    }
  }

  function renderContacts() {
    const data = siteState.blocks?.contacts || {};
    editorContainer.innerHTML = `
      <form data-form="contacts">
        <fieldset>
          <legend>Contato</legend>
          <div class="editor-list">
            <label>Nome comercial
              <input name="name" type="text" value="${valueOrEmpty(data.name)}" placeholder="EFTX Broadcast & Telecom">
            </label>
            <label>Telefone(s)
              <input name="phone" type="text" value="${valueOrEmpty(data.phone)}" placeholder="(19) 98145-6085 / (19) 4117-0270">
            </label>
            <label>E-mail principal
              <input name="email" type="email" value="${valueOrEmpty(data.email)}" placeholder="contato@eftx.com.br">
            </label>
            <label>WhatsApp
              <input name="whatsapp" type="text" value="${valueOrEmpty(data.whatsapp)}" placeholder="5519998537007">
            </label>
            <label>Endereço
              <input name="address" type="text" value="${valueOrEmpty(data.address)}" placeholder="Rua Higyno Guilherme Costato, 298 - Valinhos/SP">
            </label>
            <label>Mapa (iframe embed)
              <textarea name="map_embed" rows="3">${valueOrEmpty(data.map_embed)}</textarea>
            </label>
          </div>
        </fieldset>
        <fieldset>
          <legend>Redes sociais</legend>
          <div class="editor-list">
            <label>Instagram
              <input name="instagram" type="url" value="${valueOrEmpty(data.instagram)}" placeholder="https://www.instagram.com/iftx_broadcast/">
            </label>
            <label>Facebook
              <input name="facebook" type="url" value="${valueOrEmpty(data.facebook)}" placeholder="https://www.facebook.com/iftxbroadcast">
            </label>
            <label>LinkedIn
              <input name="linkedin" type="url" value="${valueOrEmpty(data.linkedin)}" placeholder="https://www.linkedin.com/company/iftx-broadcast-television-radio">
            </label>
          </div>
        </fieldset>
        <div class="flex-row">
          <button type="submit" class="btn">Salvar contatos</button>
        </div>
      </form>
    `;

    const form = editorContainer.querySelector('form');
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const payload = {};
      formData.forEach((value, key) => {
        if (value instanceof File) {
          return;
        }
        const trimmed = String(value).trim();
        if (trimmed) {
          payload[key] = trimmed;
        }
      });
      postJSON(endpoints.contacts, payload)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });
  }

  function createListItem(fields) {
    const wrapper = document.createElement('div');
    wrapper.className = 'editor-item';
    wrapper.innerHTML = fields;
    const removeButton = wrapper.querySelector('[data-action="remove-item"]');
    if (removeButton) {
      removeButton.addEventListener('click', () => {
        wrapper.remove();
      });
    }
    return wrapper;
  }

  function renderHero() {
    const promos = Array.isArray(siteState.blocks?.hero_promos) ? siteState.blocks.hero_promos : [];
    const images = Array.isArray(siteState.blocks?.hero_images) ? siteState.blocks.hero_images : [];
    editorContainer.innerHTML = `
      <div class="editor-section">
        <h2>Mensagens do Hero</h2>
        <div class="editor-list" data-list="hero-promos"></div>
        <div class="flex-row">
          <button type="button" class="btn is-secondary" data-action="add-hero-promo">Adicionar destaque</button>
          <button type="button" class="btn" data-action="save-hero-promos">Salvar destaques</button>
        </div>
      </div>
      <div class="editor-section">
        <h2>Imagens do Hero</h2>
        <div class="upload-control">
          <label>Carregar nova imagem
            <input type="file" accept="image/*" data-upload="hero-image">
          </label>
          <small>Formatos aceitos: png, jpg, jpeg, webp, svg.</small>
        </div>
        <div class="editor-list" data-list="hero-images"></div>
        <div class="flex-row">
          <button type="button" class="btn is-secondary" data-action="add-hero-image">Adicionar imagem</button>
          <button type="button" class="btn" data-action="save-hero-images">Salvar imagens</button>
        </div>
      </div>
    `;

    const promosList = editorContainer.querySelector('[data-list="hero-promos"]');
    promos.forEach((item) => {
      const fields = `
        <label>Título
          <input type="text" data-field="title" value="${valueOrEmpty(item.title)}">
        </label>
        <label>Descrição
          <textarea rows="3" data-field="description">${valueOrEmpty(item.description)}</textarea>
        </label>
        <label>Imagem personalizada (opcional)
          <input type="text" data-field="image" placeholder="uploads/images/..." value="${valueOrEmpty(item.image)}">
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      promosList.appendChild(createListItem(fields));
    });

    const imagesList = editorContainer.querySelector('[data-list="hero-images"]');
    images.forEach((item) => {
      const fields = `
        <label>URL da imagem
          <input type="text" data-field="image" value="${valueOrEmpty(item.image)}" placeholder="uploads/images/...">
        </label>
        <label>Legenda (opcional)
          <input type="text" data-field="title" value="${valueOrEmpty(item.title)}">
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      const node = createListItem(fields);
      if (item.image) {
        const preview = document.createElement('img');
        preview.src = item.image;
        preview.alt = item.title || 'Imagem hero';
        preview.style.maxHeight = '80px';
        preview.style.maxWidth = '100%';
        preview.style.borderRadius = '6px';
        preview.style.objectFit = 'cover';
        preview.style.border = '1px solid rgba(10, 78, 139, 0.15)';
        preview.style.marginBottom = '0.5rem';
        node.insertBefore(preview, node.firstChild);
      }
      imagesList.appendChild(node);
    });

    editorContainer.querySelector('[data-action="add-hero-promo"]').addEventListener('click', () => {
      const fields = `
        <label>Título
          <input type="text" data-field="title" value="">
        </label>
        <label>Descrição
          <textarea rows="3" data-field="description"></textarea>
        </label>
        <label>Imagem personalizada (opcional)
          <input type="text" data-field="image" placeholder="uploads/images/...">
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      promosList.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="add-hero-image"]').addEventListener('click', () => {
      const fields = `
        <label>URL da imagem
          <input type="text" data-field="image" placeholder="uploads/images/...">
        </label>
        <label>Legenda (opcional)
          <input type="text" data-field="title" placeholder="Observação para o slider">
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      imagesList.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="save-hero-promos"]').addEventListener('click', () => {
      const payload = { items: [] };
      promosList.querySelectorAll('.editor-item').forEach((node) => {
        const title = node.querySelector('[data-field="title"]').value.trim();
        const description = node.querySelector('[data-field="description"]').value.trim();
        const image = node.querySelector('[data-field="image"]').value.trim();
        if (!title) {
          return;
        }
        payload.items.push({ title, description, image: image || null });
      });
      postJSON(endpoints.heroPromos, payload)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });

    editorContainer.querySelector('[data-action="save-hero-images"]').addEventListener('click', () => {
      const payload = { items: [] };
      imagesList.querySelectorAll('.editor-item').forEach((node) => {
        const image = node.querySelector('[data-field="image"]').value.trim();
        const title = node.querySelector('[data-field="title"]').value.trim();
        if (!image) {
          return;
        }
        payload.items.push({ image, title: title || null });
      });
      postJSON(endpoints.heroImages, payload)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });

    const uploadInput = editorContainer.querySelector('[data-upload="hero-image"]');
    if (uploadInput) {
      uploadInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (!files || !files.length) {
          return;
        }
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('section', 'hero');
        postForm(endpoints.uploadImage, formData)
          .then((response) => {
            if (response.status === 'ok') {
              showStatus('Imagem carregada. Atualize a lista para utilizá-la.');
              refreshState();
            }
          })
          .catch((error) => showStatus(error.message, 'error'))
          .finally(() => {
            uploadInput.value = '';
          });
      });
    }
  }

  function renderHighlights() {
    const highlights = Array.isArray(siteState.blocks?.highlights) ? siteState.blocks.highlights : [];
    editorContainer.innerHTML = `
      <div class="editor-section">
        <h2>Pilares e destaques</h2>
        <div class="editor-list" data-list="highlights"></div>
        <div class="flex-row">
          <button type="button" class="btn is-secondary" data-action="add-highlight">Adicionar pilar</button>
          <button type="button" class="btn" data-action="save-highlights">Salvar pilares</button>
        </div>
      </div>
    `;
    const listNode = editorContainer.querySelector('[data-list="highlights"]');
    highlights.forEach((item) => {
      const fields = `
        <label>Título
          <input type="text" data-field="title" value="${valueOrEmpty(item.title)}">
        </label>
        <label>Descrição
          <textarea rows="3" data-field="description">${valueOrEmpty(item.description)}</textarea>
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      listNode.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="add-highlight"]').addEventListener('click', () => {
      const fields = `
        <label>Título
          <input type="text" data-field="title">
        </label>
        <label>Descrição
          <textarea rows="3" data-field="description"></textarea>
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      listNode.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="save-highlights"]').addEventListener('click', () => {
      const payload = { items: [] };
      listNode.querySelectorAll('.editor-item').forEach((node) => {
        const title = node.querySelector('[data-field="title"]').value.trim();
        const description = node.querySelector('[data-field="description"]').value.trim();
        if (!title) {
          return;
        }
        payload.items.push({ title, description });
      });
      postJSON(endpoints.highlights, payload)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });
  }

  function renderGallery() {
    const gallery = Array.isArray(siteState.blocks?.gallery) ? siteState.blocks.gallery : [];
    editorContainer.innerHTML = `
      <div class="editor-section">
        <h2>Galeria institucional</h2>
        <div class="upload-control">
          <label>Carregar imagem na galeria
            <input type="file" accept="image/*" data-upload="gallery-image">
          </label>
          <small>Utilize imagens otimizadas. Após o upload, elas aparecem na lista abaixo.</small>
        </div>
        <div class="editor-list" data-list="gallery"></div>
        <div class="flex-row">
          <button type="button" class="btn is-secondary" data-action="add-gallery">Adicionar imagem</button>
          <button type="button" class="btn" data-action="save-gallery">Salvar galeria</button>
        </div>
      </div>
    `;
    const listNode = editorContainer.querySelector('[data-list="gallery"]');
    gallery.forEach((item) => {
      const fields = `
        <label>URL da imagem
          <input type="text" data-field="image" value="${valueOrEmpty(item.image)}" placeholder="uploads/images/...">
        </label>
        <label>Legenda (opcional)
          <input type="text" data-field="title" value="${valueOrEmpty(item.title)}">
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      const node = createListItem(fields);
      if (item.image) {
        const preview = document.createElement('img');
        preview.src = item.image;
        preview.alt = item.title || 'Galeria';
        preview.style.maxHeight = '80px';
        preview.style.borderRadius = '6px';
        preview.style.border = '1px solid rgba(10, 78, 139, 0.15)';
        preview.style.objectFit = 'cover';
        preview.style.marginBottom = '0.5rem';
        node.insertBefore(preview, node.firstChild);
      }
      listNode.appendChild(node);
    });

    editorContainer.querySelector('[data-action="add-gallery"]').addEventListener('click', () => {
      const fields = `
        <label>URL da imagem
          <input type="text" data-field="image" placeholder="uploads/images/...">
        </label>
        <label>Legenda (opcional)
          <input type="text" data-field="title">
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      listNode.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="save-gallery"]').addEventListener('click', () => {
      const payload = { items: [] };
      listNode.querySelectorAll('.editor-item').forEach((node) => {
        const image = node.querySelector('[data-field="image"]').value.trim();
        const title = node.querySelector('[data-field="title"]').value.trim();
        if (!image) {
          return;
        }
        payload.items.push({ image, title: title || null });
      });
      postJSON(endpoints.gallery, payload)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });

    const uploadInput = editorContainer.querySelector('[data-upload="gallery-image"]');
    if (uploadInput) {
      uploadInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (!files || !files.length) {
          return;
        }
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('section', 'gallery');
        postForm(endpoints.uploadImage, formData)
          .then(() => refreshState())
          .catch((error) => showStatus(error.message, 'error'))
          .finally(() => {
            uploadInput.value = '';
          });
      });
    }
  }

  function renderFaq() {
    const faq = Array.isArray(siteState.blocks?.faq) ? siteState.blocks.faq : [];
    editorContainer.innerHTML = `
      <div class="editor-section">
        <h2>Perguntas frequentes</h2>
        <div class="editor-list" data-list="faq"></div>
        <div class="flex-row">
          <button type="button" class="btn is-secondary" data-action="add-faq">Adicionar pergunta</button>
          <button type="button" class="btn" data-action="save-faq">Salvar FAQ</button>
        </div>
      </div>
    `;
    const listNode = editorContainer.querySelector('[data-list="faq"]');
    faq.forEach((item) => {
      const fields = `
        <label>Pergunta
          <input type="text" data-field="question" value="${valueOrEmpty(item.question)}">
        </label>
        <label>Resposta
          <textarea rows="3" data-field="answer">${valueOrEmpty(item.answer)}</textarea>
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      listNode.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="add-faq"]').addEventListener('click', () => {
      const fields = `
        <label>Pergunta
          <input type="text" data-field="question">
        </label>
        <label>Resposta
          <textarea rows="3" data-field="answer"></textarea>
        </label>
        <div class="editor-item__controls">
          <button type="button" class="btn is-secondary" data-action="remove-item">Remover</button>
        </div>
      `;
      listNode.appendChild(createListItem(fields));
    });

    editorContainer.querySelector('[data-action="save-faq"]').addEventListener('click', () => {
      const payload = { items: [] };
      listNode.querySelectorAll('.editor-item').forEach((node) => {
        const question = node.querySelector('[data-field="question"]').value.trim();
        const answer = node.querySelector('[data-field="answer"]').value.trim();
        if (!question || !answer) {
          return;
        }
        payload.items.push({ question, answer });
      });
      postJSON(endpoints.faq, payload)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });
  }

  function renderDocuments() {
    const documents = Array.isArray(siteState.documents) ? siteState.documents : [];
    editorContainer.innerHTML = `
      <section class="editor-section">
        <h2>Upload de datasheet (PDF)</h2>
        <form data-form="upload-document" class="upload-control">
          <label>Selecionar PDF
            <input type="file" accept="application/pdf" name="file" required>
          </label>
          <div class="flex-row">
            <label>Título opcional
              <input type="text" name="display_name" placeholder="Nome exibido no catálogo">
            </label>
            <label>Categoria
              <input type="text" name="category" placeholder="FM, UHF, VHF...">
            </label>
          </div>
          <label>Descrição (opcional)
            <textarea name="description" rows="2" placeholder="Resumo para o catálogo"></textarea>
          </label>
          <div class="flex-row">
            <label>Thumbnail (path opcional)
              <input type="text" name="thumbnail_path" placeholder="uploads/images/...">
            </label>
            <label>
              <input type="checkbox" name="is_featured"> Destacar na home
            </label>
          </div>
          <div class="flex-row">
            <button type="submit" class="btn">Enviar PDF</button>
          </div>
        </form>
      </section>
      <section class="editor-section">
        <h2>Documentos cadastrados</h2>
        <div class="table-wrapper">
          <table class="table-docs">
            <thead>
              <tr>
                <th>Arquivo</th>
                <th>Título</th>
                <th>Categoria</th>
                <th>Descrição</th>
                <th>Thumbnail</th>
                <th class="actions">Ações</th>
              </tr>
            </thead>
            <tbody data-documents-body></tbody>
          </table>
        </div>
      </section>
    `;

    const tbody = editorContainer.querySelector('[data-documents-body]');
    documents.forEach((doc) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>
          <div><strong>${doc.filename}</strong></div>
          <small>${doc.size_label || ''} • ${doc.modified_label || ''}</small>
        </td>
        <td><input type="text" data-field="display_name" value="${valueOrEmpty(doc.display_name)}"></td>
        <td><input type="text" data-field="category" value="${valueOrEmpty(doc.category)}"></td>
        <td><textarea rows="2" data-field="description">${valueOrEmpty(doc.description)}</textarea></td>
        <td>
          <input type="text" data-field="thumbnail_path" value="${valueOrEmpty(doc.thumbnail_path)}" placeholder="uploads/images/...">
          ${doc.thumbnail_url ? `<a href="${doc.thumbnail_url}" target="_blank" rel="noopener">ver imagem</a>` : ''}
        </td>
        <td class="actions">
          <label style="display:flex;align-items:center;gap:0.35rem;">
            <input type="checkbox" data-field="is_featured" ${doc.is_featured ? 'checked' : ''}> Destaque
          </label>
          <button type="button" class="btn" data-action="save-document" data-id="${doc.id || ''}" data-filename="${doc.filename}">Salvar</button>
          <button type="button" class="btn is-secondary" data-action="delete-document" data-id="${doc.id || ''}" data-filename="${doc.filename}">Remover meta</button>
        </td>
      `;
      tbody.appendChild(row);
    });

    const uploadForm = editorContainer.querySelector('[data-form="upload-document"]');
    uploadForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const formData = new FormData(uploadForm);
      if (!formData.get('file')) {
        showStatus('Selecione um arquivo PDF para enviar.', 'error');
        return;
      }
      postForm(endpoints.uploadDocument, formData)
        .then((response) => {
          if (response.state) {
            setState(response.state);
            uploadForm.reset();
            reloadPreview();
          }
        })
        .catch((error) => showStatus(error.message, 'error'));
    });

    tbody.querySelectorAll('[data-action="save-document"]').forEach((button) => {
      button.addEventListener('click', () => {
        const row = button.closest('tr');
        const id = button.dataset.id;
        const filename = button.dataset.filename;
        const payload = {
          display_name: row.querySelector('[data-field="display_name"]').value.trim(),
          category: row.querySelector('[data-field="category"]').value.trim(),
          description: row.querySelector('[data-field="description"]').value.trim(),
          thumbnail_path: row.querySelector('[data-field="thumbnail_path"]').value.trim(),
          is_featured: row.querySelector('[data-field="is_featured"]').checked,
        };
        const url = id ? `/admin/site-designer/documents/${id}` : endpoints.documentsUpsert;
        const request = id ? postJSON(url, payload) : postJSON(url, { ...payload, filename });
        request
          .then((response) => {
            if (response.state) {
              setState(response.state);
              reloadPreview();
            }
          })
          .catch((error) => showStatus(error.message, 'error'));
      });
    });

    tbody.querySelectorAll('[data-action="delete-document"]').forEach((button) => {
      button.addEventListener('click', () => {
        const id = button.dataset.id;
        if (!id) {
          showStatus('Salve os metadados antes de tentar removê-los.', 'error');
          return;
        }
        const confirmRemoval = window.confirm('Remover metadados deste documento? (O PDF permanecerá salvo)');
        if (!confirmRemoval) {
          return;
        }
        const url = `/admin/site-designer/documents/${id}`;
        const request = deleteRequest(url);
        request
          .then((response) => {
            if (response.state) {
              setState(response.state);
              reloadPreview();
            }
          })
          .catch((error) => showStatus(error.message, 'error'));
      });
    });
  }

  menuButtons.forEach((button) => {
    button.addEventListener('click', () => {
      renderSection(button.dataset.section);
    });
  });

  if (refreshButton) {
    refreshButton.addEventListener('click', () => {
      showStatus('Atualizando dados do site...');
      refreshState();
    });
  }

  if (reloadPreviewButton) {
    reloadPreviewButton.addEventListener('click', reloadPreview);
  }

  if (toggleDeviceButton) {
    toggleDeviceButton.addEventListener('click', () => {
      const next = previewDevice === 'desktop' ? 'mobile' : 'desktop';
      updateDeviceView(next);
      reloadPreview();
    });
  }

  renderSection(currentSection);
  updateDeviceView(previewDevice);
})();
