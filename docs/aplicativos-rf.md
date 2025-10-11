# Aplicativos de RF – Guia Técnico

A página **/aplicativos-rf** reúne calculadoras especializadas de RF e micro-ondas alinhadas ao catálogo da EFTX. Todas as ferramentas utilizam o core numérico em `app/rs_core/` e herdam o layout autenticado (`base.html`).

## Calculadoras disponíveis
- Conversão de S-parâmetros – |S| linear/dB, fase, Γ, ρ, RL, VSWR.
- VSWR ↔ Return Loss ↔ |Γ| – conversões bidirecionais estáveis.
- dB ↔ módulo linear – amplitude (20·log₁₀) e potência (10·log₁₀).
- Microfita Hammerstad/Jensen – largura `W` para Z₀ informado.
- Guias de onda retangulares – frequências de corte TE/TM e propagação.
- Linha de transmissão – comprimento elétrico, fase, λg, β.
- Perda total em cabos EFTX – interpolação log-log a partir do PostgreSQL.
- Difração por borda de faca – ITU-R P.526 com gráfico Ld(v).

## Fórmulas empregadas

### S-parâmetros
- |S|₍dB₎ = 20·log₁₀|S|.
- Γ = |S|·e^{jφ}, ρ = |Γ|.
- VSWR = (1 + |Γ|)/(1 − |Γ|).
- Return Loss (dB) = −20·log₁₀|Γ|.
- Perda por desadaptação (dB) = −10·log₁₀(1 − |Γ|²).

**Exemplo:** |S| = 0.5 e φ = −45°. Resultado: −6.021 dB, VSWR = 3.000, RL = 6.021 dB, mismatch = 1.249 dB.

### VSWR / RL / |Γ|
- |Γ| = (VSWR − 1)/(VSWR + 1).
- VSWR = (1 + |Γ|)/(1 − |Γ|).
- RL(dB) = −20·log₁₀|Γ|.

**Exemplo:** VSWR = 1.20 → |Γ| = 0.0909, RL = 20.828 dB, mismatch = 0.036 dB.

### dB ↔ linear
- Amplitude: dB = 20·log₁₀(x) ⇔ x = 10^{dB/20}.
- Potência: dB = 10·log₁₀(x) ⇔ x = 10^{dB/10}.

**Exemplo:** −3.000 dB (amplitude) → 0.708 (linear).

### Microfita Hammerstad/Jensen
- Modelagem iterativa usando W/h, εᵣ e espessura `t` com correção ΔW/h.
- Restrições: 0.1 ≲ W/h ≲ 20 para erro < 1% (alerta exibido fora da faixa).

**Exemplo:** εᵣ = 4.3, h = 1.6 mm, t = 35 µm, Z₀ = 50 Ω → W = 3.046 mm, W/h = 1.904, ε_eff = 3.268.

### Guias retangulares
- f_c = (c/2)·√[(m/a)² + (n/b)²].
- λ_g = λ₀/√(1 − (f_c/f)²), β = 2π/λ_g para f > f_c.

**Exemplo:** Guia WR-90 (a = 22.86 mm, b = 10.16 mm), modo TE₁₀ → f_c = 6.557 GHz. A 10 GHz: λ_g = 39.707 mm, β = 158.238 rad/m.

### Linha de transmissão
- λ₀ = c/f.
- vₚ = vf·c ou c/√ε_eff.
- λ_g = vₚ/f, β = 2π/λ_g, fase = β·L (mod 360°).

**Exemplo:** f = 100 MHz, vf = 0.82, L = 2.5 m → λ_g = 2.458 m, fase = 6.107°.
- Inverso: mesma configuração para fase 90° → L = 0.615 m.

### Perdas em cabos EFTX
- Atenuação cadastrada como curva JSONB (`attenuation_db_per_100m_curve`).
- Interpolação log-log entre pontos (frequência × dB/100 m). Extrapolação linear em log quando fora da faixa, com alerta.
- Perda total = (L/100)·α(f) + Σ(perdas conectores).

**Workflow:** `services/cabos_service.calcular_perda_total` → busca `Cable` via SQLAlchemy, normaliza curva, aplica interpolação, retorna detalhes (origem, VF, velocidade). O formulário notifica extrapolações e exibe pontos de apoio usados.

**Exemplo:** Cabo com α(500 MHz) = 5.2 dB/100 m, L = 80 m, conectores [0.20, 0.15] → perda cabo = 4.160 dB, conectores = 0.350 dB, total = 4.510 dB.

### Difração borda de faca (ITU-R P.526)
- Parâmetro v = h·√(2/λ · (d₁ + d₂)/(d₁·d₂)).
- L_d(v) = 0 dB (v ≤ −0.7); caso contrário 6.9 + 20·log₁₀(√((v − 0.1)² + 1) + v − 0.1).
- r₁ = √(λ·d₁·d₂/(d₁ + d₂)) (1ª zona de Fresnel), clearance = h_obstáculo − h_los.

**Exemplo:** f = 2.4 GHz, d₁ = 5.0 km, d₂ = 6.5 km, h_tx = 35 m, h_rx = 28 m, h_obs = 55 m → v = 1.734, L_d = 17.906 dB, r₁ = 18.789 m, clearance = 1.226·r₁.

## Integração com o banco de cabos
1. Blueprint carrega os modelos disponíveis via `cabos_service.listar_cabos()`.
2. Cálculo chama `calcular_perda_total()` com id, frequência (Hz), comprimento (m) e lista de perdas adicionais.
3. O serviço extrai pontos da curva JSONB (`{ "points": [{"frequency_mhz": 100, "attenuation": 4.1}, ...] }` ou `{ "100": 4.1, "300": 6.5 }`).
4. Interpolação log-log garante continuidade em décadas diferentes. Extrapolações retornam `extrapolado=True` para alerta na UI.
5. Velocity factor (`velocity_factor`) é retornado com velocidade de propagação (`vf·c`) quando disponível.

## Estendendo os aplicativos
- Adicione novas funções numéricas em `app/rs_core/` com dependências puras.
- Registre serviços auxiliares em `app/services/` quando houver acesso a dados.
- Crie formulário WTForms em `app/blueprints/aplicativos_rf/forms.py` e trate no `routes.py` com identificador exclusivo.
- Reaproveite a estrutura de cards no template (`templates/aplicativos_rf/index.html`), adicionando tooltip, botão “Copiar” e âncora na lista lateral.
- Documente fórmulas e exemplos aqui e inclua testes em `tests/rs_core/` ou `tests/blueprints/`.

## Referências
- ITU-R P.526-15 – Difração por obstáculos isolados.
- Pozar, D. M. *Microwave Engineering*, 4ª ed. (Hammerstad & Jensen, Sec. 3.9).
- Collin, R. E. *Foundations for Microwave Engineering* – parâmetros S e adaptação.
